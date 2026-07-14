"""Pipeline orchestration: Separation -> Clean -> Analysis -> Render -> Outputs."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from . import audio_io
from .document import EditDocument
from .stages import breath, clean, dynamics, gate, render, separation, sibilance


# Remix peak ceiling: the sum is scaled DOWN (never up) to keep this much
# headroom; equal scaling preserves the vocal-to-instrumental relationship.
REMIX_PEAK_CEILING_DB = -1.0


def mix_remix(vocal: np.ndarray, instrumental: np.ndarray, vocal_trim_db: float = 0.0) -> np.ndarray:
    """Sum cleaned vocal (trimmed by vocal_trim_db) with the instrumental."""
    n = min(vocal.shape[1], instrumental.shape[1])
    remix = vocal[:, :n] * 10 ** (vocal_trim_db / 20) + instrumental[:, :n]
    ceiling = 10 ** (REMIX_PEAK_CEILING_DB / 20)
    peak = np.max(np.abs(remix))
    if peak > ceiling:
        remix = remix * (ceiling / peak)
    return remix


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
    # Trim applied to the cleaned vocal ONLY in the remix sum (the exported
    # vocal stem is unaffected). Restores backing-track balance when leveling
    # pushes the singer forward.
    remix_vocal_db: float = 0.0
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
            # Field-test calibration: leveling pushed the singer slightly too
            # far forward in the remix; sit the vocal back down ~2 dB.
            s.remix_vocal_db = -2.0
        return s


def analyze(vocal: np.ndarray, sr: int, settings: Settings) -> EditDocument:
    """Run all analysis modules over a (cleaned) vocal, produce the Edit Document."""
    mono = audio_io.to_mono(vocal)
    doc = EditDocument(sample_rate=sr, duration=len(mono) / sr, mode=settings.mode)

    pauses, vad_times, vad_mask = gate.analyze(
        mono, sr, min_pause_s=settings.min_pause_s, floor_db=settings.gate_floor_db
    )
    # Guards are always recorded, so render protects speech from breath dips
    # (and from hand-edited pauses) even when the gate module is off.
    doc.speech_guards = gate.speech_guards(vad_times, vad_mask)
    if settings.enable_gate:
        doc.pauses = pauses

    if settings.enable_dynamics:
        doc.gain_curve, info = dynamics.analyze(
            mono, sr, speech_times=vad_times, speech_mask=vad_mask,
            target_db=settings.target_db, speed_ms=settings.dynamics_speed_ms,
            smoothing=settings.dynamics_smoothing, catch_peaks=settings.catch_peaks,
        )
        doc.analysis["dynamics"] = info

    if settings.enable_breath:
        doc.breaths = breath.analyze(
            mono, sr, vad_times, vad_mask, reduction_db=settings.breath_reduction_db
        )
        # Energy VADs flag breaths as speech, which would guard them against
        # their own reduction. The breath detector has spectral evidence the
        # VAD lacks, so detected breaths are punched out of the guards.
        if doc.breaths:
            doc.speech_guards = gate.subtract_intervals(
                doc.speech_guards, [[b.start, b.end] for b in doc.breaths]
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
        remix = mix_remix(cleaned, instrumental, settings.remix_vocal_db)
        doc.analysis["remix"] = {
            "vocal_trim_db": settings.remix_vocal_db,
            "peak_ceiling_db": REMIX_PEAK_CEILING_DB,
        }
        audio_io.save(out_dir / "remix.wav", remix, sr)
        outputs["remix"] = str(out_dir / "remix.wav")

    doc.save(out_dir / "edit_document.json")
    outputs["edit_document"] = str(out_dir / "edit_document.json")
    return outputs
