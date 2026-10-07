"""Mix stage (Phase 2): make a cleaned vocal sound produced, then seat it in the track.

Clean (Phase 0/1) *repairs* a vocal; Mix *shapes* it. Same contract as every
other module: analysis MEASURES the vocal and writes every decision into the
Edit Document (``doc.mix``); render applies that document deterministically
(the reverb's noise is seeded, so identical input renders bit-identically);
every move is bounded and reported; any part can be bypassed, or hand-edited
and re-rendered with ``--from-doc``.

Vocal chain, in order:

1. **Compress** — feed-forward RMS compressor; threshold taken from the
   vocal's own active level, makeup gain loudness-neutral (the vocal comes out
   steadier, not louder). It runs FIRST because compression shifts the
   long-term tonal balance: measured on a real take, it put back +2.5 dB of
   the mud an EQ placed before it had just removed.
2. **Tone** — high-pass, then a *measured* EQ: the compressed vocal's
   long-term spectrum (vocal-active audio only) is compared with a
   produced-vocal target and the mud cut / presence boost / air shelf are set
   to close the gap, each bounded.
3. **De-ess** — split-band, level-independent: reduces the >5.5 kHz band only
   where it spikes relative to the whole voice. Runs AFTER the EQ, because a
   presence/air boost would otherwise undo the Sibilance module's work.
4. **Space** — plate-style reverb (seeded synthetic impulse response, FFT
   convolution) and a tempo-synced slapback, both as sends whose loudness is
   set relative to the dry vocal.

Backing: a small bounded **pocket** dip where the vocal's clarity lives.
Bus: an optional gentle **glue** compressor before mastering.

Tone targets were taken from a separated professional pop vocal (presence
-6 dB, air -14.6 dB relative to the 500-1000 Hz body) and set a little short
of it, so a home vocal is moved toward "produced" without being forced there.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from .. import audio_io, dsp, measure

MIX_VERSION = 1

# Tone targets: band energy relative to the 500-1000 Hz "body" band, in dB.
TONE_TARGETS = {"mud_max_db": -4.0, "presence_db": -8.0, "air_db": -17.0}
TONE_BOUNDS = {"mud_cut_db": 4.0, "presence_boost_db": 6.0, "presence_cut_db": 3.0,
               "air_boost_db": 5.0, "air_cut_db": 2.0}
# A source is bandwidth-limited (an MP3/phone low-pass) when its 16-20 kHz
# energy sits this far below its 8-14 kHz energy: there is no real air to lift,
# only codec noise, so the air shelf is capped hard. Measured on separated
# stems: 128 kb/s MP3 -35 dB; home WAV, studio master and pocketed phone WAV
# -12 to -25 dB.
HF_LIMITED_DB = -30.0
AIR_LIMITED_MAX_BOOST_DB = 1.5


# --------------------------------------------------------------------- filters


def _peak_sos(fs: int, f0: float, gain_db: float, q: float) -> np.ndarray:
    """RBJ cookbook peaking EQ as one second-order section."""
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * min(f0, fs * 0.45) / fs
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * a, -2 * np.cos(w0), 1 - alpha * a]
    den = [1 + alpha / a, -2 * np.cos(w0), 1 - alpha / a]
    return np.array([[b[0] / den[0], b[1] / den[0], b[2] / den[0], 1.0,
                      den[1] / den[0], den[2] / den[0]]])


def _high_shelf_sos(fs: int, f0: float, gain_db: float, slope: float = 1.0) -> np.ndarray:
    """RBJ cookbook high shelf as one second-order section."""
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * min(f0, fs * 0.45) / fs
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2 * np.sqrt((a + 1 / a) * (1 / slope - 1) + 2)
    sa = 2 * np.sqrt(a) * alpha
    b0 = a * ((a + 1) + (a - 1) * cw + sa)
    b1 = -2 * a * ((a - 1) + (a + 1) * cw)
    b2 = a * ((a + 1) + (a - 1) * cw - sa)
    a0 = (a + 1) - (a - 1) * cw + sa
    a1 = 2 * ((a - 1) - (a + 1) * cw)
    a2 = (a + 1) - (a - 1) * cw - sa
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])


def _butter(fs: int, hz: float, btype: str, order: int = 2) -> np.ndarray:
    return signal.butter(order, min(hz, fs * 0.45) / (fs / 2), btype=btype, output="sos")


def apply_eq(audio: np.ndarray, sr: int, tone: dict) -> np.ndarray:
    """Apply a tone dict (high-pass + bands) to (channels, samples) audio."""
    sos = []
    if tone.get("highpass_hz"):
        sos.append(_butter(sr, float(tone["highpass_hz"]), "high"))
    for band in tone.get("bands", []):
        g = float(band.get("gain_db", 0.0))
        if abs(g) < 0.05:
            continue
        if band.get("type") == "high_shelf":
            sos.append(_high_shelf_sos(sr, float(band["hz"]), g))
        else:
            sos.append(_peak_sos(sr, float(band["hz"]), g, float(band.get("q", 1.0))))
    if not sos:
        return np.atleast_2d(audio).astype(np.float64)
    return signal.sosfilt(np.vstack(sos), np.atleast_2d(audio).astype(np.float64), axis=1)


# ------------------------------------------------------------------- measuring


def _active(audio: np.ndarray, sr: int, intervals: list) -> np.ndarray:
    act = measure.active_audio(audio, sr, intervals) if intervals else np.atleast_2d(audio)
    return act if act.shape[1] >= int(measure.MIN_ACTIVE_S * sr) else np.atleast_2d(audio)


def tone_profile(audio: np.ndarray, sr: int, intervals: list | None = None) -> dict:
    """Long-term band energies relative to the 500-1000 Hz body, in dB."""
    mono = audio_io.to_mono(_active(audio, sr, intervals or []))
    f, p = signal.welch(mono.astype(np.float64), sr, nperseg=min(8192, max(256, len(mono))))

    def band(lo, hi):
        return 10 * np.log10(np.sum(p[(f >= lo) & (f < hi)]) + 1e-20)

    body = band(500, 1000)
    upper = band(8000, min(14000, sr * 0.45))
    return {
        "mud_db": round(band(200, 500) - body, 2),
        "presence_db": round(band(2000, 5000) - body, 2),
        "air_db": round(upper - body, 2),
        "sibilance_db": round(band(5500, min(10000, sr * 0.45)) - body, 2),
        # How much top end exists above 16 kHz relative to 8-14 kHz.
        "hf_extension_db": (round(band(16000, 20000) - upper, 2) if sr >= 44100 else None),
    }


def plan_tone(profile: dict, highpass_hz: float = 85.0, targets: dict | None = None) -> dict:
    """Turn a measured tone profile into bounded EQ decisions."""
    t = {**TONE_TARGETS, **(targets or {})}
    b = TONE_BOUNDS
    notes = []
    mud_cut = float(np.clip(profile["mud_db"] - t["mud_max_db"], 0.0, b["mud_cut_db"]))
    pres = float(np.clip(t["presence_db"] - profile["presence_db"],
                         -b["presence_cut_db"], b["presence_boost_db"]))
    air = float(np.clip(t["air_db"] - profile["air_db"], -b["air_cut_db"], b["air_boost_db"]))
    for name, want, got in (("presence", t["presence_db"] - profile["presence_db"], pres),
                            ("air", t["air_db"] - profile["air_db"], air)):
        if abs(want - got) > 0.05:
            notes.append(f"{name} wanted {want:+.1f} dB, bounded to {got:+.1f} dB")
    hf = profile.get("hf_extension_db")
    limited = hf is None or hf < HF_LIMITED_DB
    if limited and air > AIR_LIMITED_MAX_BOOST_DB:
        air = AIR_LIMITED_MAX_BOOST_DB
        notes.append("source looks bandwidth-limited (phone/MP3): air boost capped "
                     f"at {AIR_LIMITED_MAX_BOOST_DB:+.1f} dB")
    return {
        "highpass_hz": highpass_hz,
        "bands": [
            {"type": "peak", "hz": 300.0, "gain_db": round(-mud_cut, 2), "q": 1.0, "label": "mud"},
            {"type": "peak", "hz": 3200.0, "gain_db": round(pres, 2), "q": 0.7, "label": "presence"},
            {"type": "high_shelf", "hz": 8000.0, "gain_db": round(air, 2), "label": "air"},
        ],
        "measured": profile,
        "targets": t,
        "notes": notes,
    }


def estimate_tempo(audio: np.ndarray, sr: int, lo_bpm: float = 70.0,
                   hi_bpm: float = 180.0) -> tuple[float | None, float]:
    """Tempo from onset-strength autocorrelation. Returns (bpm or None, confidence)."""
    mono = audio_io.to_mono(audio).astype(np.float64)
    hop, win = 512, 1024
    if len(mono) < sr * 8:
        return None, 0.0
    _, _, z = signal.stft(mono, sr, nperseg=win, noverlap=win - hop, boundary=None)
    mag = np.log1p(np.abs(z))
    flux = np.maximum(np.diff(mag, axis=1), 0).sum(axis=0)
    flux = flux - flux.mean()
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    fps = sr / hop
    lags = np.arange(len(ac))
    ok = (lags >= fps * 60 / hi_bpm) & (lags <= fps * 60 / lo_bpm)
    if not ok.any() or ac[0] <= 0:
        return None, 0.0
    best = lags[ok][np.argmax(ac[ok])]
    conf = float(ac[best] / ac[0])
    return round(60 * fps / best, 1), round(conf, 3)


# ----------------------------------------------------------------- dynamics


def _block_levels(audio: np.ndarray, sr: int, hop_s: float = 0.001,
                  window_s: float = 0.010) -> tuple[np.ndarray, int]:
    """Smoothed RMS level (dBFS) per hop block, from the loudest channel's power."""
    power = np.max(np.atleast_2d(audio).astype(np.float64) ** 2, axis=0)
    hop = max(1, int(hop_s * sr))
    n_blocks = int(np.ceil(len(power) / hop))
    blocks = np.pad(power, (0, n_blocks * hop - len(power))).reshape(n_blocks, hop).mean(axis=1)
    k = max(1, int(window_s / hop_s))
    smoothed = np.convolve(blocks, np.ones(k) / k, mode="same")
    return 10 * np.log10(smoothed + 1e-12), hop


def _ballistics(target_gr_db: np.ndarray, hop_s: float, attack_ms: float,
                release_ms: float) -> np.ndarray:
    """One-pole attack/release smoothing of a gain-reduction curve (dB, >= 0)."""
    a_att = 1 - np.exp(-hop_s / max(attack_ms / 1000, 1e-4))
    a_rel = 1 - np.exp(-hop_s / max(release_ms / 1000, 1e-4))
    out = np.empty_like(target_gr_db)
    acc = 0.0
    for i, v in enumerate(target_gr_db):
        acc += (a_att if v > acc else a_rel) * (v - acc)
        out[i] = acc
    return out


def _gain_curve_to_samples(gr_db: np.ndarray, hop: int, n: int) -> np.ndarray:
    t_blocks = (np.arange(len(gr_db)) + 0.5) * hop
    return 10 ** (-np.interp(np.arange(n), t_blocks, gr_db) / 20)


def compress(audio: np.ndarray, sr: int, threshold_db: float, ratio: float,
             attack_ms: float, release_ms: float, knee_db: float = 6.0) -> tuple[np.ndarray, dict]:
    """Feed-forward soft-knee compressor. Returns (audio, report). No makeup here."""
    x = np.atleast_2d(audio).astype(np.float64)
    level, hop = _block_levels(x, sr)
    over = level - threshold_db
    slope = 1 - 1 / max(ratio, 1.0)
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, over * slope,
                           slope * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    gr = _ballistics(gr, hop / sr, attack_ms, release_ms)
    out = x * _gain_curve_to_samples(gr, hop, x.shape[1])[None, :]
    loud = level > threshold_db - 20
    return out, {
        "max_gr_db": round(float(gr.max(initial=0.0)), 2),
        "mean_active_gr_db": round(float(gr[loud].mean()) if loud.any() else 0.0, 2),
    }


def _loudness_match(processed: np.ndarray, reference: np.ndarray, sr: int, intervals: list,
                    max_db: float = 6.0) -> tuple[np.ndarray, float]:
    """Scale `processed` so its active loudness equals `reference`'s (bounded)."""
    ref, _ = measure.active_lufs(reference, sr, intervals)
    got, _ = measure.active_lufs(processed, sr, intervals)
    if ref is None or got is None:
        return processed, 0.0
    g = float(np.clip(ref - got, -max_db, max_db))
    return processed * 10 ** (g / 20), g


def deess(audio: np.ndarray, sr: int, split_hz: float = 5500.0, threshold_db: float = -10.0,
          amount: float = 0.6, max_reduction_db: float = 6.0) -> tuple[np.ndarray, dict]:
    """Level-independent split-band de-esser.

    The high band is reduced only where it rises above ``threshold_db`` relative
    to the whole voice at that moment — so a quiet "s" and a loud one are
    treated alike, and vowels (high band far below the voice) are untouched.
    """
    x = np.atleast_2d(audio).astype(np.float64)
    low = np.empty_like(x)
    high = np.empty_like(x)
    for ch in range(x.shape[0]):
        low[ch], high[ch] = dsp.band_split(x[ch], sr, split_hz)
    full_db, hop = _block_levels(x, sr, window_s=0.005)
    high_db, _ = _block_levels(high, sr, window_s=0.005)
    excess = (high_db - full_db) - threshold_db
    gr = np.clip(excess * amount, 0.0, max_reduction_db)
    gr[full_db < -60] = 0.0
    gr = _ballistics(gr, hop / sr, attack_ms=1.0, release_ms=40.0)
    out = low + high * _gain_curve_to_samples(gr, hop, x.shape[1])[None, :]
    return out, {"max_reduction_db": round(float(gr.max(initial=0.0)), 2),
                 "pct_time_active": round(100 * float(np.mean(gr > 0.5)), 1)}


# --------------------------------------------------------------------- space


def plate_ir(sr: int, rt60_s: float, predelay_ms: float, hp_hz: float, lp_hz: float,
             channels: int, seed: int) -> np.ndarray:
    """Deterministic plate-style impulse response, energy-normalised per channel."""
    n = int((predelay_ms / 1000 + rt60_s * 1.2) * sr)
    pre = int(predelay_ms / 1000 * sr)
    t = np.arange(n - pre) / sr
    env = np.exp(-6.91 * t / max(rt60_s, 0.05))
    rng = np.random.default_rng(seed)
    ir = np.zeros((channels, n))
    sos = np.vstack([_butter(sr, hp_hz, "high"), _butter(sr, lp_hz, "low")])
    for ch in range(channels):
        tail = signal.sosfilt(sos, rng.standard_normal(n - pre)) * env
        ir[ch, pre:] = tail / (np.sqrt(np.sum(tail**2)) + 1e-12)
    return ir


def _set_relative_level(wet: np.ndarray, dry: np.ndarray, sr: int, level_db: float,
                        intervals: list) -> tuple[np.ndarray, float]:
    dry_l, _ = measure.active_lufs(dry, sr, intervals)
    wet_l, _ = measure.active_lufs(wet, sr, intervals)
    if dry_l is None or wet_l is None:
        return wet * 0.0, 0.0
    g = (dry_l + level_db) - wet_l
    return wet * 10 ** (g / 20), g


def space(audio: np.ndarray, sr: int, params: dict, intervals: list) -> tuple[np.ndarray, dict]:
    """Reverb + slapback as sends; returns dry + wet at the same length."""
    x = np.atleast_2d(audio).astype(np.float64)
    n = x.shape[1]
    wet_total = np.zeros_like(x)
    report = {}

    rv = params.get("reverb") or {}
    if rv and rv.get("on", True):
        ir = plate_ir(sr, rv["rt60_s"], rv["predelay_ms"], rv["hp_hz"], rv["lp_hz"],
                      x.shape[0], int(rv.get("seed", 7)))
        wet = np.vstack([signal.fftconvolve(x[ch], ir[ch])[:n] for ch in range(x.shape[0])])
        wet, g = _set_relative_level(wet, x, sr, float(rv["level_db"]), intervals)
        wet_total += wet
        report["reverb_gain_db"] = round(g, 2)

    dl = params.get("delay") or {}
    if dl and dl.get("on", True):
        d = int(float(dl["time_s"]) * sr)
        sos = np.vstack([_butter(sr, dl["hp_hz"], "high"), _butter(sr, dl["lp_hz"], "low")])
        src = signal.sosfilt(sos, x, axis=1)
        wet = np.zeros_like(x)
        for k in range(1, int(dl.get("repeats", 3)) + 1):
            if k * d >= n:
                break
            wet[:, k * d:] += src[:, : n - k * d] * float(dl["feedback"]) ** (k - 1)
        wet, g = _set_relative_level(wet, x, sr, float(dl["level_db"]), intervals)
        wet_total += wet
        report["delay_gain_db"] = round(g, 2)

    return x + wet_total, report


# ------------------------------------------------------------------ planning


def _or(value, default):
    return default if value is None else value


def analyze(vocal: np.ndarray, sr: int, instrumental: np.ndarray | None,
            intervals: list, settings) -> dict:
    """Measure the cleaned vocal (and backing) and write every Mix decision."""
    level, _ = _block_levels(_active(vocal, sr, intervals), sr)
    active = level[level > np.max(level) - 40]
    threshold = float(np.median(active)) if len(active) else -24.0
    comp = {"threshold_db": round(threshold + settings.mix_comp_threshold_offset_db, 2),
            "ratio": settings.mix_comp_ratio, "attack_ms": 8.0, "release_ms": 120.0,
            "knee_db": 6.0, "makeup": "loudness_neutral"}

    # Tone is planned on the vocal as the EQ will actually receive it.
    compressed, _ = compress(vocal, sr, comp["threshold_db"], comp["ratio"],
                             comp["attack_ms"], comp["release_ms"], comp["knee_db"])
    tone = plan_tone(tone_profile(compressed, sr, intervals),
                     highpass_hz=settings.mix_highpass_hz)

    bpm, conf = (None, 0.0)
    if instrumental is not None:
        bpm, conf = estimate_tempo(instrumental, sr)
    # Note-synced slapback when the tempo is trustworthy, else a classic 120 ms.
    # Autocorrelation often lands on half-tempo, so halve the eighth note until
    # it is slapback-short (an eighth at the true tempo, or a sixteenth).
    delay_time = 0.12
    if bpm and conf >= 0.2:
        synced = 30.0 / bpm
        while synced > 0.3:
            synced /= 2
        if synced >= 0.08:
            delay_time = synced

    return {
        "version": MIX_VERSION,
        "bypass": {k: False for k in ("tone", "compress", "deess", "space", "pocket", "glue")},
        "compress": comp,
        "tone": tone,
        "deess": {"split_hz": 5500.0, "threshold_db": -10.0, "amount": 0.6,
                  "max_reduction_db": 6.0},
        "space": {
            # A None level in Settings switches that send off; the document
            # still carries usable parameters so it can be switched on by hand.
            "reverb": {"on": settings.mix_reverb_db is not None, "rt60_s": 1.3,
                       "predelay_ms": 25.0, "hp_hz": 250.0, "lp_hz": 7000.0,
                       "level_db": _or(settings.mix_reverb_db, -18.0), "seed": 7},
            "delay": {"on": settings.mix_delay_db is not None, "time_s": round(delay_time, 4),
                      "feedback": 0.25, "repeats": 3, "hp_hz": 300.0, "lp_hz": 5000.0,
                      "level_db": _or(settings.mix_delay_db, -22.0),
                      "tempo_bpm": bpm, "tempo_confidence": conf},
        },
        "pocket": {"hz": 2800.0, "gain_db": -abs(settings.mix_pocket_db), "q": 0.9},
        "balance": {"mode": settings.balance_mode,
                    "vocal_forward_db": settings.vocal_forward_db},
        "glue": {"ratio": 1.6, "attack_ms": 30.0, "release_ms": 250.0, "knee_db": 8.0,
                 "threshold_offset_db": 2.0},
    }


# ------------------------------------------------------------------ rendering


def render_vocal(vocal: np.ndarray, sr: int, mix: dict, intervals: list) -> tuple[np.ndarray, dict]:
    """Apply the vocal chain in ``mix`` to a cleaned vocal. Same length out."""
    bypass = mix.get("bypass", {})
    x = np.atleast_2d(vocal).astype(np.float64)
    reference = x
    report: dict = {}
    if not bypass.get("compress"):
        c = mix["compress"]
        x, rep = compress(x, sr, c["threshold_db"], c["ratio"], c["attack_ms"],
                          c["release_ms"], c.get("knee_db", 6.0))
        report["compress"] = rep
    if not bypass.get("tone"):
        x = apply_eq(x, sr, mix["tone"])
        report["tone"] = {b["label"]: b["gain_db"] for b in mix["tone"]["bands"]}
    if not bypass.get("deess"):
        d = mix["deess"]
        x, report["deess"] = deess(x, sr, d["split_hz"], d["threshold_db"], d["amount"],
                                   d["max_reduction_db"])
    # Loudness-neutral: the chain changes tone and steadiness, not level.
    x, makeup = _loudness_match(x, reference, sr, intervals)
    report["makeup_db"] = round(makeup, 2)
    if not bypass.get("space"):
        x, report["space"] = space(x, sr, mix["space"], intervals)
    return x.astype(np.float32), report


def render_backing(instrumental: np.ndarray, sr: int, mix: dict) -> np.ndarray:
    if mix.get("bypass", {}).get("pocket"):
        return np.atleast_2d(instrumental)
    p = mix["pocket"]
    tone = {"bands": [{"type": "peak", "hz": p["hz"], "gain_db": p["gain_db"], "q": p["q"]}]}
    return apply_eq(instrumental, sr, tone).astype(np.float32)


def glue(audio: np.ndarray, sr: int, mix: dict, intervals: list) -> tuple[np.ndarray, dict]:
    """Gentle, loudness-neutral bus compression that makes the stems sit together."""
    if mix.get("bypass", {}).get("glue") or not mix.get("glue"):
        return audio, {"applied": False}
    gl = mix["glue"]
    level, _ = _block_levels(_active(audio, sr, intervals), sr)
    active = level[level > np.max(level) - 40]
    thr = float(np.median(active)) + gl["threshold_offset_db"] if len(active) else -20.0
    out, rep = compress(audio, sr, thr, gl["ratio"], gl["attack_ms"], gl["release_ms"],
                        gl["knee_db"])
    out, makeup = _loudness_match(out, np.atleast_2d(audio), sr, intervals)
    return out.astype(np.float32), {"applied": True, "threshold_db": round(thr, 2),
                                    "makeup_db": round(makeup, 2), **rep}


def compute_forward_balance(vocal: np.ndarray, instrumental: np.ndarray, sr: int,
                            intervals: list, vocal_forward_db: float,
                            max_instr_db: float = 9.0, max_vocal_db: float = 3.0) -> dict:
    """Seat the vocal ``vocal_forward_db`` LU above the backing while it sings.

    The instrumental moves first (the vocal's level was set by the chain), the
    vocal covers any remainder, both bounded; a miss is reported, never forced.
    """
    v, basis = measure.active_lufs(vocal, sr, intervals)
    i, _ = measure.active_lufs(instrumental, sr, intervals)
    report = {"method": "forward", "measurement_basis": basis, "target_ratio_db": vocal_forward_db,
              "vocal_gain_db": 0.0, "instr_gain_db": 0.0, "residual_db": 0.0}
    if v is None or i is None:
        report.update(method="skipped", reason="a stem was too short or silent to measure")
        return report
    ratio = v - i
    correction = vocal_forward_db - ratio  # + means the vocal must come up relative
    instr_gain = float(np.clip(-correction, -max_instr_db, max_instr_db))
    remainder = correction + instr_gain
    vocal_gain = float(np.clip(remainder, -max_vocal_db, max_vocal_db))
    residual = remainder - vocal_gain
    report.update(ratio_before_db=round(ratio, 2), vocal_gain_db=round(vocal_gain, 2),
                  instr_gain_db=round(instr_gain, 2), residual_db=round(residual, 2))
    if abs(residual) > 0.1:
        report["reason"] = "correction exceeded stem bounds; residual reported"
    return report
