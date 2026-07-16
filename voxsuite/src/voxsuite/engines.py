"""Real engine adapter for the Fused orchestrator.

Wires the abstract `Engines` protocol to the actual pipelines mapped in
design/fused-orchestrator.md:

- isolate → voxpolish.stages.separation.separate  (once; stem feeds both)
- analyze → voxanalysis engine: pitch_track.analyze_wav + run_v2_analysis
            + report_builder.build_v2_report  (on the isolated stem)
- polish  → voxpolish Session.create(voice mode) + render  (on the same stem)

Imports are lazy and per-call so this module loads even where the heavy audio
deps (audio-separator / RoFormer, librosa, parselmouth, ffmpeg) are absent —
those environments simply fail the relevant stage with a clear message, while
`isolate` degrades gracefully (treats the upload as an already-vocal signal).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .orchestrator import IsolateResult, JobMeta


def _analysis_root() -> Path:
    env = os.environ.get("VOX_ANALYSIS_ROOT")
    if env:
        return Path(env)
    # repo-root/voxanalysis/vox-analysis  (monorepo dev layout)
    return Path(__file__).resolve().parents[3] / "voxanalysis" / "vox-analysis"


class RealEngines:
    """Drives the installed engines. Construct with a base workdir; each job
    gets its own subdir under it."""

    # ---------------------------------------------------------------- isolate
    def isolate(self, src: Path, workdir: Path) -> IsolateResult:
        src = Path(src)
        try:
            from voxpolish.stages import separation
            from voxpolish import audio_io
        except Exception as exc:  # deps not importable → treat upload as vocal
            return IsolateResult(stem=src, skipped=True, note=f"separation unavailable ({exc})")
        try:
            vocal, _instrumental, sr = separation.separate(src)
            stem = Path(workdir) / "vocal_stem.wav"
            audio_io.save(stem, vocal, sr)
            return IsolateResult(stem=stem, skipped=False, note="isolated once")
        except Exception as exc:  # model/weights/ffmpeg missing at runtime
            return IsolateResult(stem=src, skipped=True, note=f"separation failed ({exc})")

    # ---------------------------------------------------------------- analyze
    def analyze(self, stem: Path, workdir: Path, meta: JobMeta) -> dict:
        root = _analysis_root()
        engine_dir, viewer_dir = str(root / "engine"), str(root / "viewer")
        for p in (engine_dir, viewer_dir):
            if p not in sys.path:
                sys.path.insert(0, p)
        import pitch_track  # type: ignore
        import report_builder  # type: ignore

        job_dir = Path(workdir) / "analysis"
        job_dir.mkdir(parents=True, exist_ok=True)
        duration = pitch_track.probe_duration(Path(stem))
        pitch = pitch_track.analyze_wav(Path(stem), duration)
        analysis_rel, report_rel = pitch_track.run_v2_analysis(Path(stem), job_dir, meta.performer)
        raw = json.loads((job_dir / analysis_rel).read_text())
        # build_v2_report(raw, conditions="", comparison=None): song/artist are
        # recording *context* here — the fused path has no reference-comparison
        # pipeline, so comparison is honestly None (it used to receive the artist
        # name as the "recording conditions", polluting the report).
        context = " · ".join(x for x in (
            f"song: {meta.song}" if meta.song else "",
            f"original artist: {meta.artist}" if meta.artist else "",
        ) if x)
        report = report_builder.build_v2_report(raw, conditions=context, comparison=None)
        return {
            "report_path": str(job_dir / report_rel),
            "score": report.get("score"),
            "headline": report.get("headline"),
            "contour": pitch.get("contour"),
            "duration_seconds": pitch.get("duration_seconds"),
            "robust_min_note": pitch.get("robust_min_note"),
            "robust_max_note": pitch.get("robust_max_note"),
            "report": report,
        }

    # ----------------------------------------------------------------- polish
    def polish(self, stem: Path, workdir: Path, meta: JobMeta) -> dict:
        from voxpolish.pipeline import Settings
        from voxpolish.server.session import Session

        session_dir = Path(workdir) / "polish"
        session_dir.mkdir(parents=True, exist_ok=True)
        session = Session.create(
            Path(stem), session_dir,
            settings=Settings.for_mode("voice"), tune=meta.tune,
            display_name=meta.performer or "take",
        )
        session.render()
        doc = session.document()
        return {
            "download_path": str(session.root / "vocal_cleaned.wav"),
            "revision": session.revision(),
            "document": json.loads(doc.to_json()) if hasattr(doc, "to_json") else None,
        }
