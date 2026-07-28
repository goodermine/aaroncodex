"""Validity gates — run first, and everything downstream depends on them.

The rule from the spec: when a gate fails, SUPPRESS the affected metrics rather
than emitting them with a caveat. A number that survives into a report gets
believed regardless of what the footnote says. This repo has proved that twice
over — `reliability: "medium — verify by ear"` has shipped for months and nobody
has ever verified by ear.

Each gate declares:
  * what it measures, and the evidence behind its call
  * which metric groups it invalidates
  * whether it has passed its synthetic-degradation test (`validated`)

An unvalidated gate is reported but never used to suppress anything, and the
report says it was not run. A detector nobody can check is worse than no
detector: it lends degraded numbers the authority of having passed validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

# Metric groups a gate can invalidate. Names match the report sections.
SPECTRAL = "spectral"          # metallic index, resonance, alpha ratio, sfr
QUALITY = "quality"            # HNR, CPPS, jitter, shimmer
DYNAMICS = "dynamics"          # level range, phrase shaping
INTONATION = "intonation"      # deviation, drift, scoop depth
PITCH = "pitch"                # f0 itself and everything derived from it
FORMANTS = "formants"          # F1-F3, vowel space, H2-F1
PHRASE_END = "phrase_end"      # sag, offset type
EVERYTHING = "everything"


@dataclass
class GateResult:
    name: str
    passed: bool                     # True = input is clean on this axis
    severity: str                    # "ok" | "warn" | "fail"
    evidence: dict = field(default_factory=dict)
    invalidates: tuple = ()
    validated: bool = False          # has this gate passed its synthetic test?
    measurable: bool = True          # was there enough material to judge at all?

    def to_dict(self) -> dict:
        d = asdict(self)
        d["invalidates"] = list(self.invalidates)
        if not self.measurable:
            d["note"] = ("This gate had insufficient material to measure. It certifies "
                         "nothing — absence of a failure here is not evidence of a clean "
                         "recording.")
        elif not self.validated:
            d["note"] = ("This gate has no passing synthetic-degradation test, so it "
                         "suppresses nothing. Treat the affected metrics as unchecked, "
                         "not as verified clean.")
        return d


def _frame_rms_db(y: np.ndarray, hop: int = 512, win: int = 2048) -> np.ndarray:
    n = max(1, (len(y) - win) // hop)
    out = np.empty(n)
    for i in range(n):
        seg = y[i * hop: i * hop + win]
        out[i] = np.sqrt(np.mean(seg * seg) + 1e-20)
    return 20 * np.log10(np.maximum(out, 1e-10))


# ─────────────────────────────────────────────────────────── gates

def gate_clipping(y: np.ndarray, sr: int, **_) -> GateResult:
    """Samples pinned at the ceiling, and flat-topped runs.

    Percentage alone is a weak signal — a legitimately hot mix touches full scale.
    Consecutive identical extreme samples are the signature of true clipping.
    """
    peak = float(np.max(np.abs(y))) + 1e-12
    at_ceiling = np.abs(y) >= 0.999 * peak
    pct = float(np.mean(at_ceiling) * 100)
    runs, run = 0, 0
    for v in at_ceiling:
        run = run + 1 if v else 0
        if run == 3:
            runs += 1
    per_sec = runs / (len(y) / sr)
    bad = pct > 0.05 or per_sec > 1.0
    return GateResult("clipping", not bad, "fail" if bad else "ok",
                      {"pct_samples_at_ceiling": round(pct, 4),
                       "flat_top_runs_per_second": round(per_sec, 2)},
                      (EVERYTHING,), validated=True)


def gate_snr(y: np.ndarray, sr: int, **_) -> GateResult:
    """Voiced level against the noise floor, both taken from the level histogram.

    The floor is the 5th percentile of frame level, the signal the 90th. Anything
    under ~20 dB puts the periodicity measures on sand.
    """
    db = _frame_rms_db(y)
    floor, sig = float(np.percentile(db, 5)), float(np.percentile(db, 90))
    snr = sig - floor
    bad = snr < 20.0
    return GateResult("snr", not bad, "fail" if bad else ("warn" if snr < 28 else "ok"),
                      {"snr_db": round(snr, 1), "noise_floor_db": round(floor, 1)},
                      (QUALITY, SPECTRAL), validated=True)


def gate_reverb(y: np.ndarray, sr: int, hop: int = 512, **_) -> GateResult:
    """Decay time after phrase offsets — an RT60 proxy.

    Measured as T20: how long the level takes to fall 20 dB below where it sat
    just before the offset, scaled to RT60. Only offsets followed by a real gap
    count — a first attempt fitted a slope over the 300 ms after every offset and
    got POSITIVE slopes on 89% of them, because in dense singing the next phrase
    starts inside that window. It was measuring onsets and calling them decay.
    """
    db = _frame_rms_db(y, hop=hop)
    fps = sr / hop
    active = db > (np.percentile(db, 90) - 25)
    offsets = np.where(active[:-1] & ~active[1:])[0]
    span = int(1.0 * fps)
    t20 = []
    for o in offsets:
        pre = db[max(0, o - int(0.1 * fps)): o]
        tail = db[o: o + span]
        if len(pre) < 3 or len(tail) < span // 3:
            continue
        if active[o + 1: o + 1 + len(tail)].mean() > 0.25:
            continue                      # the next phrase intrudes; not a clean tail
        target = float(np.median(pre)) - 20.0
        below = np.where(tail <= target)[0]
        if len(below):
            t20.append(below[0] / fps)
    if len(t20) < 3:
        return GateResult("reverb", True, "unknown",
                          {"n_clean_offsets": len(t20),
                           "note": "too few isolated phrase endings to measure decay"},
                          (QUALITY, PHRASE_END, SPECTRAL),
                          validated=REVERB_VALIDATED, measurable=False)
    rt60 = float(np.median(t20)) * 3.0
    bad = rt60 > 0.8
    return GateResult("reverb", not bad, "fail" if bad else ("warn" if rt60 > 0.5 else "ok"),
                      {"rt60_estimate_s": round(rt60, 2),
                       "median_t20_s": round(float(np.median(t20)), 3),
                       "n_clean_offsets": len(t20)},
                      (QUALITY, PHRASE_END, SPECTRAL), validated=REVERB_VALIDATED)


def gate_compression(y: np.ndarray, sr: int, **_) -> GateResult:
    """Crest factor and level spread, both over ACTIVE frames only.

    Measured across the whole file the crest factor is dominated by the silence
    between phrases and barely moves under 8:1 compression (22.1 -> 20.0 dB on a
    real vocal stem). Restricted to frames that actually contain singing it
    separates cleanly: 13.5 -> 6.6 dB, with the level IQR falling 11.3 -> 6.7 dB.
    """
    db = _frame_rms_db(y)
    act = db > (np.percentile(db, 90) - 25)
    if act.sum() < 20:
        return GateResult("compression", True, "ok",
                          {"note": "too little active audio to judge"}, (DYNAMICS,),
                          validated=True)
    lin = 10 ** (db[act] / 20.0)
    crest = float(20 * np.log10(lin.max() / (np.sqrt(np.mean(lin ** 2)) + 1e-12)))
    iqr = float(np.percentile(db[act], 75) - np.percentile(db[act], 25))
    bad = crest < 9.0 or iqr < 8.0
    return GateResult("compression", not bad, "fail" if bad else ("warn" if crest < 11 else "ok"),
                      {"crest_factor_active_db": round(crest, 1),
                       "level_iqr_active_db": round(iqr, 1)},
                      (DYNAMICS, QUALITY), validated=True)


def gate_pitch_correction(y: np.ndarray, sr: int, f0: np.ndarray | None = None,
                          hop: int = 512, **_) -> GateResult:
    """How tightly f0 clusters on the semitone grid.

    Natural singing scatters around the grid; correction pins it. Measured as the
    share of voiced frames within 10 cents of a semitone, against the ~17% that
    would occur by chance on a uniform distribution.
    """
    if f0 is None:
        import librosa
        f0, _, _ = librosa.pyin(y, fmin=70, fmax=900, sr=sr, hop_length=hop)
    v = f0[np.isfinite(f0)]
    if len(v) < 50:
        return GateResult("pitch_correction", True, "ok",
                          {"note": "too few voiced frames to judge"}, (), validated=True)
    cents = 1200 * np.log2(v / 440.0)
    dev = np.abs((cents + 50) % 100 - 50)
    on_grid = float(np.mean(dev < 10) * 100)
    bad = on_grid > 45.0
    return GateResult("pitch_correction", not bad, "fail" if bad else ("warn" if on_grid > 35 else "ok"),
                      {"pct_within_10c_of_semitone": round(on_grid, 1),
                       "chance_level_pct": 20.0},
                      (INTONATION,), validated=True)


def gate_eq(y: np.ndarray, sr: int, **_) -> GateResult:
    """A shelf shows as a KNEE in the long-term average spectrum, not as tilt.

    Overall tilt cannot carry this: a +9 dB shelf moved it from -9.6 to -6.5
    dB/octave on a real vocal, and -6.5 is a perfectly plausible voice. Any
    absolute threshold either fires on normal singing or never fires at all.
    A shelf instead makes the upper band's slope diverge from the lower band's,
    and that difference is comparable within one file.
    """
    import librosa
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=1024))
    ltas = 20 * np.log10(np.maximum(S.mean(axis=1), 1e-10))
    fr = librosa.fft_frequencies(sr=sr, n_fft=4096)
    def tilt(lo, hi):
        b = (fr >= lo) & (fr <= hi)
        return float(np.polyfit(np.log2(fr[b]), ltas[b], 1)[0])
    low, high = tilt(300, 2000), tilt(2500, 9000)
    knee = high - low                     # positive = upper band lifted relative to lower
    bad = knee > 6.0
    return GateResult("eq", not bad, "fail" if bad else ("warn" if knee > 3.0 else "ok"),
                      {"tilt_300_2000_db_per_oct": round(low, 2),
                       "tilt_2500_9000_db_per_oct": round(high, 2),
                       "knee_db_per_oct": round(knee, 2)},
                      (SPECTRAL,), validated=EQ_VALIDATED)


def gate_pitch_track(y: np.ndarray, sr: int, f0: np.ndarray | None = None,
                     voiced_prob: np.ndarray | None = None, hop: int = 512, **_) -> GateResult:
    """Tracker confidence and octave jumps.

    An octave error is a 1200-cent step between adjacent frames. They are the
    failure mode that inflated drift measurements in this project before.
    """
    if f0 is None:
        import librosa
        f0, _, voiced_prob = librosa.pyin(y, fmin=70, fmax=900, sr=sr, hop_length=hop)
    v = f0[np.isfinite(f0)]
    if len(v) < 20:
        return GateResult("pitch_track", False, "fail",
                          {"voiced_frames": int(len(v))}, (PITCH, INTONATION), validated=True)
    cents = 1200 * np.log2(v / 440.0)
    steps = np.abs(np.diff(cents))
    jumps = float(np.mean((steps > 1000) & (steps < 1400)) * 100)
    if voiced_prob is not None:
        vp = np.asarray(voiced_prob)[np.isfinite(f0)]      # voiced frames only:
        conf = float(np.nanmean(vp)) if len(vp) else float("nan")   # averaging over
    else:                                                  # silence buries it
        conf = float("nan")
    bad = jumps > 1.0
    return GateResult("pitch_track", not bad, "fail" if bad else "ok",
                      {"pct_octave_jumps": round(jumps, 2),
                       "mean_voiced_confidence": None if np.isnan(conf) else round(conf, 3)},
                      (PITCH, INTONATION), validated=True)


# ── Which gates have passed their synthetic-degradation test ────────────────
#
# Measured 28 Jul against a real vocal stem plus deliberately damaged copies
# (tests/test_standalone_gates.py). A gate marked False is REPORTED but never
# suppresses anything, and the report says the axis was not checked.
#
#   clipping          VALIDATED  clean passes, +6 dB overdrive caught
#                                (0.068% pinned samples, 2.98 flat-top runs/s)
#   snr               VALIDATED  clean passes, 12 dB pink noise caught (17.7 dB)
#   compression       VALIDATED  clean passes, 8:1 caught — but only once crest
#                                factor is measured on ACTIVE frames; over the
#                                whole file silence dominates it and 8:1 moved it
#                                just 22.1 -> 20.0 dB. Active-only: 13.5 -> 6.6.
#   pitch_correction  VALIDATED  clean sits at chance (19.3% within 10 c of the
#                                grid, chance ~20%); quantised hits 46.6%
#   pitch_track       VALIDATED  clean 0.47% octave jumps; 3% injected -> 5.7%
#
#   reverb            NOT VALIDATED. The T20 measurement is sound but needs
#                     phrase endings followed by a real gap, and dense singing
#                     supplies none — 0 usable endings in 45 s of real vocal. It
#                     reports "unknown" rather than "clean", because on this
#                     material it genuinely cannot tell.
#   eq                NOT VALIDATED. There is no absolute threshold that works
#                     without a reference. A +9 dB shelf moved the overall tilt
#                     from -9.6 to -6.5 dB/octave, and -6.5 is an ordinary voice;
#                     the two-band knee test fared no better (-2.17 on the
#                     shelved copy). Detecting EQ from one file with no reference
#                     may not be possible, and a detector that cannot be checked
#                     is worse than none.
REVERB_VALIDATED = False
EQ_VALIDATED = False

ALL_GATES = (gate_clipping, gate_snr, gate_reverb, gate_compression,
             gate_pitch_correction, gate_eq, gate_pitch_track)


def run_gates(y: np.ndarray, sr: int, **kw) -> dict:
    """Run every gate. Returns results plus the set of metric groups to suppress.

    Only VALIDATED gates suppress. An unvalidated gate is reported so the reader
    knows what was and was not checked, but it cannot silence a metric on the
    strength of a detector nobody has tested.
    """
    results = [g(y, sr, **kw) for g in ALL_GATES]
    suppressed = set()
    for r in results:
        if r.validated and not r.passed:
            suppressed.update(r.invalidates)
    unchecked = [r.name for r in results if not r.validated]
    unmeasurable = [r.name for r in results if r.validated and not r.measurable]
    return {
        "passed": all(r.passed for r in results if r.validated and r.measurable),
        "gates": {r.name: r.to_dict() for r in results},
        "suppressed_metrics": sorted(suppressed),
        "gates_not_validated": unchecked,
        "gates_not_measurable": unmeasurable,
        "coverage_note": (
            "Only gates that are BOTH validated against a synthetic degradation AND "
            "able to measure this particular recording can certify anything. Axes "
            "listed in gates_not_validated or gates_not_measurable were not checked; "
            "that is not the same as being clean."),
    }
