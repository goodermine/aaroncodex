"""Pipeline orchestration: Separation -> Clean -> Analysis -> Render -> Outputs."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from . import audio_io, measure
from .document import EditDocument
from .stages import breath, clean, dynamics, gate, master, render, separation, sibilance


def mix_remix(
    vocal: np.ndarray,
    instrumental: np.ndarray,
    vocal_db: float = 0.0,
    instr_db: float = 0.0,
) -> np.ndarray:
    """Sum the stems with per-stem gain. Peak/loudness control is mastering's job."""
    n = min(vocal.shape[1], instrumental.shape[1])
    return (
        vocal[:, :n] * 10 ** (vocal_db / 20)
        + instrumental[:, :n] * 10 ** (instr_db / 20)
    )


def compute_balance(
    raw_vocal: np.ndarray,
    cleaned_vocal: np.ndarray,
    instrumental: np.ndarray,
    sr: int,
    active_intervals: list,
    max_vocal_db: float = 3.0,
    max_instr_db: float = 2.0,
) -> dict:
    """Restore the recording's own vocal-to-backing loudness relationship.

    All loudness is measured during vocal-active sections. The correction is
    the drift the pipeline introduced (original ratio minus cleaned ratio),
    applied to the vocal stem first, overflowing to the instrumental, both
    bounded. No fixed offsets, no forcing equal LUFS.
    """
    v_raw, basis = measure.active_lufs(raw_vocal, sr, active_intervals)
    v_clean, _ = measure.active_lufs(cleaned_vocal, sr, active_intervals)
    i_act, _ = measure.active_lufs(instrumental, sr, active_intervals)

    report = {
        "measurement_basis": basis,
        "raw_vocal_active_lufs": _r(v_raw),
        "cleaned_vocal_active_lufs": _r(v_clean),
        "instrumental_active_lufs": _r(i_act),
        "vocal_gain_db": 0.0,
        "instr_gain_db": 0.0,
        "residual_db": 0.0,
        "method": "measured",
    }
    if v_raw is None or v_clean is None or i_act is None:
        report["method"] = "skipped"
        report["reason"] = "a stem was too short or silent to measure"
        return report

    ratio_orig = v_raw - i_act
    ratio_clean = v_clean - i_act
    correction = ratio_orig - ratio_clean

    vocal_gain = float(np.clip(correction, -max_vocal_db, max_vocal_db))
    remainder = correction - vocal_gain
    # Moving the instrumental the opposite way covers the remainder.
    instr_gain = float(np.clip(-remainder, -max_instr_db, max_instr_db))
    residual = correction - (vocal_gain - instr_gain)

    report.update(
        ratio_original_db=_r(ratio_orig),
        ratio_cleaned_db=_r(ratio_clean),
        correction_needed_db=_r(correction),
        vocal_gain_db=round(vocal_gain, 2),
        instr_gain_db=round(instr_gain, 2),
        residual_db=round(residual, 2),
    )
    if abs(residual) > 0.1:
        report["reason"] = "correction exceeded stem bounds; residual reported"
    return report


def _r(v):
    return None if v is None else round(float(v), 2)


# A detector must clear this confidence to override the speech guards.
GUARD_OVERRIDE_CONFIDENCE = 0.5


def confident_regions(regions: list, min_confidence: float = GUARD_OVERRIDE_CONFIDENCE) -> list:
    return [r for r in regions if getattr(r, "confidence", 1.0) >= min_confidence]


@dataclass
class Settings:
    mode: str = "voice"  # "song" | "voice"
    # In voice mode, still run separation to strip background music beds.
    strip_music_bed: bool = False
    separation_model: str = "htdemucs_ft"
    denoise_amount: float = 1.0
    enable_gate: bool = True
    enable_dynamics: bool = True
    enable_breath: bool = True
    enable_sibilance: bool = True
    gate_floor_db: float = -60.0
    min_pause_s: float = 0.35
    target_db: float | None = None
    dynamics_speed_ms: float = 600.0
    dynamics_smoothing: float = 0.7
    catch_peaks: float = 0.5
    breath_reduction_db: float = -12.0
    sibilance_sensitivity: float = 0.5
    # Manual override for the vocal's remix balance, in dB. None (default)
    # means balance is MEASURED: the original vocal-to-backing loudness ratio
    # is restored within the stem bounds below. The exported stem is never
    # affected either way.
    remix_vocal_db: float | None = None
    # Balance / mastering targets and safety bounds (all configurable).
    target_lufs: float = -15.0
    true_peak_db: float = -3.0
    max_vocal_correction_db: float = 3.0
    max_instr_correction_db: float = 2.0
    max_master_gain_db: float = 8.0
    max_limiter_gr_db: float = 3.0
    # Local dynamics safety: hard boost ceiling (after loudness-neutral
    # correction) and maximum automation slope.
    max_boost_db: float = 6.0
    max_slope_db_s: float = 6.0
    extra: dict = field(default_factory=dict)

    @classmethod
    def for_mode(cls, mode: str) -> "Settings":
        s = cls(mode=mode)
        if mode == "song":
            # Breaths are musical; gate gently and level less aggressively.
            s.gate_floor_db = -24.0
            s.min_pause_s = 0.6
            s.breath_reduction_db = -6.0
            s.dynamics_smoothing = 0.5
        return s


def analyze(vocal: np.ndarray, sr: int, settings: Settings) -> EditDocument:
    """Run all analysis modules over a (cleaned) vocal, produce the Edit Document."""
    mono = audio_io.to_mono(vocal)
    doc = EditDocument(sample_rate=sr, duration=len(mono) / sr, mode=settings.mode)

    pauses, vad_times, vad_mask = gate.analyze(
        mono, sr, min_pause_s=settings.min_pause_s, floor_db=settings.gate_floor_db
    )
    # Guards are always recorded, so render protects speech from breath dips
    # (and from hand-edited pauses) even when the gate module is off. They use
    # the wider PROTECTION mask so washed lyrics below the detection threshold
    # are covered too; measurement intervals stay on the detection mask.
    protect = gate.protection_mask(mono, sr, vad_times, vad_mask)
    doc.speech_guards = gate.speech_guards(vad_times, protect)
    doc.analysis["vocal_active"] = gate.speech_guards(vad_times, vad_mask)
    if settings.enable_gate:
        doc.pauses = pauses

    if settings.enable_dynamics:
        doc.gain_curve, info = dynamics.analyze(
            mono, sr, speech_times=vad_times, speech_mask=vad_mask,
            target_db=settings.target_db, speed_ms=settings.dynamics_speed_ms,
            smoothing=settings.dynamics_smoothing, catch_peaks=settings.catch_peaks,
            max_boost_db=settings.max_boost_db,
            max_slope_db_s=settings.max_slope_db_s,
        )
        doc.analysis["dynamics"] = info

    if settings.enable_breath:
        doc.breaths = breath.analyze(
            mono, sr, vad_times, vad_mask, reduction_db=settings.breath_reduction_db
        )
        # Energy VADs flag breaths as speech, which would guard them against
        # their own reduction. The breath detector has spectral evidence the
        # VAD lacks — but only HIGH-CONFIDENCE breaths may punch through the
        # guards. Low-confidence detections (washed lyrics look breath-like)
        # stay listed, and the guards win at render time.
        punchers = confident_regions(doc.breaths)
        if punchers:
            doc.speech_guards = gate.subtract_intervals(
                doc.speech_guards, [[b.start, b.end] for b in punchers]
            )

    if settings.enable_sibilance:
        doc.sibilants = sibilance.analyze(
            mono, sr, speech_times=vad_times, speech_mask=vad_mask,
            sensitivity=settings.sibilance_sensitivity,
        )

    doc.analysis["counts"] = {
        "pauses": len(doc.pauses),
        "breaths": len(doc.breaths),
        "sibilants": len(doc.sibilants),
    }
    return doc


def process(
    input_path: str | Path,
    out_dir: str | Path,
    settings: Settings | None = None,
    edit_doc: EditDocument | None = None,
) -> dict:
    """Full pipeline. Returns a dict of output paths.

    If edit_doc is given, analysis is skipped and that document is rendered
    instead — this is the "edit the JSON, re-render" workflow.
    """
    settings = settings or Settings()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    # Stage A: ingest (+ separation in song mode / bed-stripping voice mode).
    instrumental = None
    if settings.mode == "song" or settings.strip_music_bed:
        vocal, instrumental, sr = separation.separate(input_path, settings.separation_model)
    else:
        vocal, sr = audio_io.load(input_path)
    raw_vocal = vocal.copy()

    # Clean runs before analysis so every detector sees the denoised signal.
    vocal, denoise_info = clean.process(vocal, sr, settings.denoise_amount)

    # Stage B: analysis -> Edit Document (unless re-rendering an edited one).
    if edit_doc is None:
        doc = analyze(vocal, sr, settings)
        doc.denoise = denoise_info
    else:
        doc = edit_doc

    # Stage C: deterministic render.
    cleaned = render.render(vocal, sr, doc)

    audio_io.save(out_dir / "vocal_cleaned.wav", cleaned, sr)
    outputs["vocal_cleaned"] = str(out_dir / "vocal_cleaned.wav")

    # Diagnostic delta contract, two distinct outputs:
    #
    # removed.wav — targeted removal ONLY (denoise, gate, breath, sibilance),
    # computed against a unity-gain baseline (same doc, no dynamics curve).
    # Audible vocal/musical content in here is a bug.
    removal_render = render.render(vocal, sr, replace(doc, gain_curve=[]))
    audio_io.save(out_dir / "removed.wav", raw_vocal - removal_render, sr)
    outputs["removed"] = str(out_dir / "removed.wav")

    # full_difference.wav — raw minus final, INCLUDING intentional dynamics /
    # leveling gain. Whenever leveling is active this necessarily contains a
    # gain-scaled copy of the vocal; that is expected and not a defect.
    audio_io.save(out_dir / "full_difference.wav", raw_vocal - cleaned, sr)
    outputs["full_difference"] = str(out_dir / "full_difference.wav")

    if instrumental is not None:
        audio_io.save(out_dir / "instrumental.wav", instrumental, sr)
        outputs["instrumental"] = str(out_dir / "instrumental.wav")

        # Balance: restore the recording's own vocal-to-backing relationship
        # (or honor an explicit manual trim), then master within bounds.
        if settings.remix_vocal_db is not None:
            balance = {"method": "manual", "vocal_gain_db": settings.remix_vocal_db,
                       "instr_gain_db": 0.0}
        else:
            balance = compute_balance(
                raw_vocal, cleaned, instrumental, sr,
                doc.analysis.get("vocal_active", []),
                max_vocal_db=settings.max_vocal_correction_db,
                max_instr_db=settings.max_instr_correction_db,
            )
        remix = mix_remix(
            cleaned, instrumental, balance["vocal_gain_db"], balance["instr_gain_db"]
        )
        remix, master_report = master.master(
            remix, sr,
            target_lufs=settings.target_lufs,
            ceiling_dbtp=settings.true_peak_db,
            max_gain_db=settings.max_master_gain_db,
            max_limiter_gr_db=settings.max_limiter_gr_db,
        )
        doc.analysis["balance"] = balance
        doc.analysis["master"] = master_report
        audio_io.save(out_dir / "remix.wav", remix, sr)
        outputs["remix"] = str(out_dir / "remix.wav")

    doc.save(out_dir / "edit_document.json")
    outputs["edit_document"] = str(out_dir / "edit_document.json")
    return outputs
