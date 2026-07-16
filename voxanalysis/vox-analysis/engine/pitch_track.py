#!/usr/bin/env python3
"""Produce a reliable, browser-friendly singing pitch contour."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Some system Python/librosa installations cannot write beside the installed
# numba modules. Keep the JIT cache in an explicitly writable runtime location.
os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "vox-numba-cache"))

import librosa
import numpy as np

FMIN_NOTE = "C2"
FMAX_NOTE = "D6"
DISPLAY_RATE_HZ = 10.0
RAW_RATE_HZ = 20.0
# pYIN confidence is much lower on phone recordings with backing tracks than
# on clean isolated vocals. A lower-confidence contour is useful when clearly
# labelled as a caution, whereas genuinely insufficient pitch still fails.
RELIABLE_CONFIDENCE = 0.55
CAUTION_CONFIDENCE = 0.05
STEM_SCRIPT = Path(__file__).parent / "tools" / "stems" / "batch_stems.sh"
STEM_TIMEOUT_SECONDS = 30 * 60
SHARED_ANALYZER = Path(__file__).parent / "analyse_song.py"
V2_CALIBRATION = Path(__file__).parent / "calibration" / "pro_reference.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_FETCHER = REPO_ROOT / "scripts" / "fetch_reference.py"
COMPARE_TOOL = Path(__file__).parent / "tools" / "compare_takes.py"
SPECTRAL_EXPORTER = Path(__file__).parent / "spectral_export.py"
# The optional visual exporter must never be able to exhaust the pitch
# viewer's 30-minute global analysis budget. Keep it in a killable child,
# cap operator overrides at ten minutes, and reserve enough of the outer
# deadline to publish the already-complete core result.


def _bounded_timeout_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(value):
        return default
    return min(600.0, max(1.0, value))


SPECTRAL_EXPORT_TIMEOUT_SECONDS = _bounded_timeout_env(
    "VOX_SPECTRAL_EXPORT_TIMEOUT", 300.0
)
SPECTRAL_FINALIZATION_RESERVE_SECONDS = 30.0


class PitchTrackError(RuntimeError):
    pass


def _run_spectral_export(
    wav_path: Path,
    output_dir: Path,
    pitch_contour: dict,
    source: str,
    timeout_seconds: float,
) -> dict:
    """Run the display-only exporter in a separately bounded process."""
    completed = subprocess.run(
        [
            sys.executable,
            str(SPECTRAL_EXPORTER),
            str(wav_path),
            str(output_dir),
            source,
        ],
        input=json.dumps(pitch_contour, allow_nan=False),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode:
        detail = completed.stderr.strip().splitlines()
        raise RuntimeError(detail[-1] if detail else "spectral exporter failed")
    descriptor = json.loads(
        (output_dir / "descriptor.json").read_text(encoding="utf-8")
    )
    if (
        not isinstance(descriptor, dict)
        or descriptor.get("source") != source
        or not isinstance(descriptor.get("tiles"), list)
        or not isinstance(descriptor.get("harmonic_tracks_file"), str)
    ):
        raise RuntimeError("spectral exporter returned an invalid descriptor")
    return descriptor


def _maybe_export_spectral(
    enabled: bool,
    wav_path: Path,
    output_dir: Path,
    job_dir: Path,
    pitch_contour: dict,
    source: str,
    analysis_deadline: float | None = None,
) -> dict | None:
    if not enabled:
        return None
    try:
        timeout_seconds = SPECTRAL_EXPORT_TIMEOUT_SECONDS
        if analysis_deadline is not None:
            remaining = (
                analysis_deadline
                - time.monotonic()
                - SPECTRAL_FINALIZATION_RESERVE_SECONDS
            )
            if remaining < 1.0:
                raise TimeoutError("spectral export skipped near analysis deadline")
            timeout_seconds = min(timeout_seconds, remaining)
        descriptor = _run_spectral_export(
            wav_path,
            output_dir,
            pitch_contour,
            source,
            timeout_seconds,
        )
        artifact_bytes = sum(path.stat().st_size for path in output_dir.iterdir() if path.is_file())
        return {
            "status": "ready",
            "descriptor_file": str((output_dir / "descriptor.json").relative_to(job_dir)),
            "harmonic_tracks_file": str((output_dir / descriptor["harmonic_tracks_file"]).relative_to(job_dir)),
            "tile_count": len(descriptor["tiles"]),
            "artifact_bytes": artifact_bytes,
        }
    except Exception as exc:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(
            output_dir.with_name(output_dir.name + ".tmp"), ignore_errors=True
        )
        try:
            (job_dir / f"spectral-{source}.log").write_text(repr(exc), encoding="utf-8")
        except OSError:
            pass
        return {"status": "unavailable", "reason": "spectral_export_failed"}


def cents_from_hz(value: float) -> float:
    return 1200.0 * math.log2(value / 440.0)


def note_from_cents(value: float) -> str:
    midi = int(round(69 + value / 100.0))
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[midi % 12]}{midi // 12 - 1}"


def _run(command: list[str], error_code: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else error_code
        raise PitchTrackError(f"{error_code}: {detail}")


def _write_stage(stage_file: Path | None, stage: str) -> None:
    if stage_file is None:
        return
    temporary = stage_file.with_suffix(".tmp")
    temporary.write_text(json.dumps({"stage": stage}), encoding="utf-8")
    temporary.replace(stage_file)


def _unlink_temporary_audio(path: Path) -> None:
    """Never fail a completed analysis because optional cleanup was denied."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def run_v2_analysis(wav_path: Path, job_dir: Path, performer_name: str) -> tuple[str, str]:
    """Run the shared calibrated VOXAI analysis in an isolated job."""
    if not SHARED_ANALYZER.is_file() or not V2_CALIBRATION.is_file():
        raise PitchTrackError("v2_analysis_failed: shared VOXAI engine or calibration is unavailable")
    work_dir = job_dir / "v2"
    work_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(SHARED_ANALYZER),
        str(wav_path.resolve()),
        "--name",
        performer_name,
        "--no-convert",
        "--calibration",
        str(V2_CALIBRATION),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=STEM_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise PitchTrackError("v2_analysis_failed: VOXAI V2 timed out") from exc
    (job_dir / "v2-analysis.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "VOXAI V2 failed"
        raise PitchTrackError(f"v2_analysis_failed: {message}")
    base_name = wav_path.stem
    analysis_path = work_dir / "output" / f"{base_name}_analysis.json"
    report_path = work_dir / "reports" / f"{base_name}_report.md"
    if not analysis_path.is_file() or not report_path.is_file():
        raise PitchTrackError("v2_analysis_failed: VOXAI V2 did not produce its report artifacts")
    return str(analysis_path.relative_to(job_dir)), str(report_path.relative_to(job_dir))


def _json_from_output(output: str) -> dict:
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise PitchTrackError("reference_lookup_failed: reference lookup returned no usable metadata")


def _validate_reference_metadata(metadata: dict, song_name: str, original_artist: str) -> None:
    title = str(metadata.get("title") or "").lower()
    banned = (" karaoke", " cover", "tribute", "instrumental", "reaction", "tutorial", "nightcore", "sped up", "slowed")
    if any(token in title for token in banned):
        raise PitchTrackError("reference_lookup_failed: top result appears to be a cover, karaoke or altered version")
    significant_song_words = [word for word in song_name.lower().replace("'", "").split() if len(word) >= 3]
    artist_words = [word for word in original_artist.lower().replace("'", "").split() if len(word) >= 4]
    if significant_song_words and not all(word in title.replace("'", "") for word in significant_song_words):
        raise PitchTrackError("reference_lookup_failed: resolved title does not match the requested song")
    if artist_words and not any(word in title.replace("'", "") for word in artist_words):
        uploader = str(metadata.get("uploader") or "").lower()
        if not any(word in uploader for word in artist_words):
            raise PitchTrackError("reference_lookup_failed: resolved source does not identify the requested artist")


def fetch_reference(song_name: str, original_artist: str, job_dir: Path) -> tuple[Path, dict]:
    if not REFERENCE_FETCHER.is_file():
        raise PitchTrackError("reference_lookup_failed: reference fetcher is unavailable")
    query = f"{original_artist} {song_name} official audio"
    result = subprocess.run(
        [sys.executable, str(REFERENCE_FETCHER), query, "--quality", "320"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=STEM_TIMEOUT_SECONDS,
    )
    (job_dir / "reference-fetch.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    metadata = _json_from_output(result.stdout)
    if result.returncode or metadata.get("status") != "ready" or not metadata.get("path"):
        raise PitchTrackError(f"reference_lookup_failed: {metadata.get('error', 'original recording could not be resolved')}")
    path = Path(metadata["path"])
    _validate_reference_metadata(metadata, song_name, original_artist)
    if not path.is_file():
        raise PitchTrackError("reference_lookup_failed: resolved original file is unavailable")
    provenance = {
        key: metadata.get(key)
        for key in ("id", "title", "uploader", "duration_seconds", "duration", "webpage_url", "cached")
    }
    provenance.update({"requested_song": song_name, "requested_artist": original_artist, "query": query})
    return path, provenance


def _load_comparison_tool():
    spec = importlib.util.spec_from_file_location("voxai_compare_takes", COMPARE_TOOL)
    if spec is None or spec.loader is None:
        raise PitchTrackError("comparison_failed: melody comparison tool is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare_with_reference(take_json: Path, reference_json: Path) -> tuple[dict, list[float | None]]:
    tool = _load_comparison_tool()
    take, take_rate, take_data = tool.load_contour(str(take_json))
    reference, reference_rate, reference_data = tool.load_contour(str(reference_json))
    if abs(take_rate - reference_rate) > 0.01:
        raise PitchTrackError("comparison_failed: singer and original contour rates differ")
    offset_cents, semitones = tool.transposition_offset(take, reference)
    shifted_take = take - offset_cents
    path = tool.dtw_align(shifted_take, reference, take_rate)
    aligned_bins: list[list[float]] = [[] for _ in range(len(take))]
    pitch_differences: list[float] = []
    lags: list[float] = []
    for take_index, reference_index in path:
        reference_value = reference[reference_index]
        take_value = shifted_take[take_index]
        if np.isfinite(reference_value):
            aligned_bins[take_index].append(float(reference_value + offset_cents))
        if np.isfinite(reference_value) and np.isfinite(take_value):
            pitch_differences.append(float(take_value - reference_value))
        lags.append((take_index - reference_index) / take_rate)
    aligned = [round(float(np.median(values)), 1) if values else None for values in aligned_bins]
    differences = np.asarray(pitch_differences, dtype=float)
    lag_values = np.asarray(lags, dtype=float)
    take_score = take_data.get("technical_score") or {}
    reference_score = reference_data.get("technical_score") or {}
    comparison = {
        "method": "banded_dtw_on_voxai_v2_contours",
        "transposition_semitones": semitones,
        "median_abs_pitch_diff_cents": round(float(np.median(np.abs(differences))), 1) if len(differences) else None,
        "pct_frames_within_50_cents": round(float(np.mean(np.abs(differences) <= 50) * 100), 1) if len(differences) else None,
        "timing_spread_s": round(float(np.percentile(lag_values, 90) - np.percentile(lag_values, 10)), 2) if len(lag_values) else None,
        "singer_score": take_score.get("overall_score_0_to_10"),
        "singer_capture_fair": take_score.get("capture_fair_score_0_to_10"),
        "original_score": reference_score.get("overall_score_0_to_10"),
        "original_capture_fair": reference_score.get("capture_fair_score_0_to_10"),
        "note": "Transposition is reported and removed before melody similarity is measured. Differences may be deliberate interpretation.",
    }
    return comparison, aligned


def analyze_original(
    reference_path: Path,
    job_dir: Path,
    original_artist: str,
    export_spectral_enabled: bool = False,
) -> dict:
    reference_dir = job_dir / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(reference_path)
    vocals_path, _ = separate_stems(reference_path, reference_dir)
    wav_path = reference_dir / "analysis.wav"
    original_playback = job_dir / "original.mp3"
    _run(["ffmpeg", "-y", "-i", str(reference_path), "-vn", "-c:a", "libmp3lame", "-b:a", "160k", str(original_playback)], "conversion_failed")
    _run(["ffmpeg", "-y", "-i", str(vocals_path), "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(wav_path)], "conversion_failed")
    pitch_result = analyze_wav(wav_path, duration)
    analysis_file, report_file = run_v2_analysis(wav_path, reference_dir, original_artist)
    result = {
        "pitch": pitch_result,
        "analysis_file": str((reference_dir / analysis_file).relative_to(job_dir)),
        "report_file": str((reference_dir / report_file).relative_to(job_dir)),
    }
    if export_spectral_enabled:
        # Kept private and removed by analyze() before result publication. The
        # optional export runs only after all scoring and comparison work has
        # finished, so its bounded child cannot steal time from core analysis.
        result["_spectral_input"] = {
            "wav_path": wav_path,
            "contour": pitch_result["contour"],
        }
    else:
        _unlink_temporary_audio(wav_path)
    return result


# Backing-stem labels across separators/models: MDX/UVR use "(Instrumental)" or
# "(No Vocals)"; Mel-Band RoFormer writes the residual as "(other)"; Demucs uses
# "no_vocals"/"other"/"accompaniment". Any of these is the non-vocal stem.
_BACKING_STEM_TOKENS = (
    "instrumental", "no_vocals", "no vocals", "other",
    "accompaniment", "backing", "karaoke", "music",
)


def _classify_stem(text: str) -> str | None:
    """Return "vocals" or "instrumental" for a stem label / filename, or None.

    Checked backing-first because a separator's model name can itself contain
    "vocals" (e.g. "vocals_mel_band_roformer"), so the residual file is only
    distinguishable by its stem label — "(other)", "(Instrumental)", etc."""
    text = text.lower()
    if any(token in text for token in _BACKING_STEM_TOKENS):
        return "instrumental"
    if "vocal" in text:
        return "vocals"
    return None


def _find_stem(stem_dir: Path, kind: str) -> Path | None:
    files = sorted(path for path in stem_dir.rglob("*") if path.is_file())
    for path in files:
        if path.suffix.lower() not in {".wav", ".flac", ".mp3", ".m4a"}:
            continue
        # Prefer the parenthesised stem label the separators emit
        # ("upload_(Vocals)_<model>", "upload_(other)_<model>"): the model name
        # itself contains "vocals", so classify on the label, not the filename.
        name = path.name.lower()
        label = re.search(r"\(([^)]+)\)", name)
        if _classify_stem(label.group(1) if label else name) == kind:
            return path
    return None


def separate_stems(input_path: Path, job_dir: Path) -> tuple[Path, Path]:
    """Run the repository's UVR helper and return vocal and backing stems."""
    if not STEM_SCRIPT.is_file():
        raise PitchTrackError("stem_separation_failed: VOXAI stem helper is unavailable")
    stem_dir = job_dir / "stems"
    stem_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["bash", str(STEM_SCRIPT), "--input", str(input_path), "--output", str(stem_dir)],
            capture_output=True,
            text=True,
            timeout=STEM_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise PitchTrackError("stem_separation_failed: vocal isolation timed out") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "UVR stem separation failed"
        raise PitchTrackError(f"stem_separation_failed: {message}")
    vocals = _find_stem(stem_dir, "vocals")
    instrumental = _find_stem(stem_dir, "instrumental")
    if not vocals or not instrumental:
        raise PitchTrackError("stem_separation_failed: both vocals and instrumental stems are required")
    return vocals, instrumental


def probe_duration(input_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(input_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise PitchTrackError("unsupported_media: ffprobe could not decode the upload")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise PitchTrackError("unsupported_media: media duration is unavailable") from exc


def _sample_contour(
    f0: np.ndarray,
    confidence: np.ndarray,
    frame_rate: float,
    target_rate: float,
    minimum_confidence: float | None = None,
) -> tuple[list[float | None], list[float | None], list[bool]]:
    step = max(1, int(round(frame_rate / target_rate)))
    values: list[float | None] = []
    confidences: list[float | None] = []
    low_confidence: list[bool] = []
    for start in range(0, len(f0), step):
        hz_bin = f0[start : start + step]
        confidence_bin = confidence[start : start + step]
        pitched = np.isfinite(hz_bin)
        if not np.any(pitched):
            values.append(None)
            confidences.append(None)
            low_confidence.append(False)
            continue
        selected = pitched
        uncertain = False
        if minimum_confidence is not None:
            reliable = (
                pitched
                & np.isfinite(confidence_bin)
                & (confidence_bin >= minimum_confidence)
            )
            if np.any(reliable):
                selected = reliable
            else:
                # A finite F0 was detected, but the bin does not contain
                # reliable evidence. Preserve the pitch for a visibly
                # uncertain trace instead of turning detected singing into a
                # false silence gap.
                uncertain = True
        cents = np.array([cents_from_hz(float(hz)) for hz in hz_bin[selected]])
        center = float(np.median(cents))
        # Drop isolated octave/tracker outliers inside the time bin.
        close = np.abs(cents - center) <= 350.0
        if not np.any(close):
            values.append(None)
            confidences.append(None)
            low_confidence.append(False)
            continue
        values.append(round(float(np.median(cents[close])), 1))
        selected_confidence = confidence_bin[selected][close]
        selected_confidence = selected_confidence[
            np.isfinite(selected_confidence)
        ]
        confidences.append(
            round(float(np.median(selected_confidence)), 3)
            if len(selected_confidence)
            else None
        )
        low_confidence.append(uncertain)
    return values, confidences, low_confidence


def _canonical_display_contour(
    f0: np.ndarray,
    confidence: np.ndarray,
    frame_rate: float,
    target_rate: float,
) -> tuple[list[float | None], list[float | None], list[bool]]:
    """Match the persisted VOXAI analysis contour used by reports/PDFs.

    pYIN has already made the voiced/unvoiced decision by returning NaN for
    unreliable pitch. Keep every remaining voiced sample at the canonical
    display cadence instead of applying a second hard confidence gate that
    creates false gaps in karaoke and phone captures.
    """
    step = max(1, int(round(frame_rate / target_rate)))
    values: list[float | None] = []
    confidences: list[float | None] = []
    low_confidence: list[bool] = []
    for index in range(0, len(f0), step):
        hz = float(f0[index])
        probability = float(confidence[index])
        if not math.isfinite(hz):
            values.append(None)
            confidences.append(None)
            low_confidence.append(False)
            continue
        values.append(round(cents_from_hz(hz), 1))
        confidences.append(round(probability, 3) if math.isfinite(probability) else None)
        low_confidence.append(
            not math.isfinite(probability) or probability < RELIABLE_CONFIDENCE
        )
    return values, confidences, low_confidence


def analyze_wav(wav_path: Path, duration_seconds: float) -> dict:
    y, sr = librosa.load(wav_path, sr=44100, mono=True)
    if not len(y):
        raise PitchTrackError("unsupported_media: decoded audio is empty")
    f0, voiced, probability = librosa.pyin(
        y,
        fmin=librosa.note_to_hz(FMIN_NOTE),
        fmax=librosa.note_to_hz(FMAX_NOTE),
        sr=sr,
        frame_length=2048,
        hop_length=512,
    )
    voiced = np.asarray(voiced, dtype=bool)
    f0 = np.asarray(f0, dtype=float).copy()
    f0[~voiced] = np.nan
    probability = np.asarray(probability, dtype=float)
    probability[~voiced] = 0.0
    frame_rate = sr / 512.0
    display, display_confidence, display_low_confidence = _canonical_display_contour(
        f0, probability, frame_rate, DISPLAY_RATE_HZ
    )
    # Preserve the established diagnostic values/confidence path. A second
    # metadata-only pass classifies bins without changing those values.
    raw, raw_confidence, _ = _sample_contour(
        f0,
        probability,
        frame_rate,
        RAW_RATE_HZ,
    )
    _, _, raw_low_confidence = _sample_contour(
        f0,
        probability,
        frame_rate,
        RAW_RATE_HZ,
        RELIABLE_CONFIDENCE,
    )
    voiced_values = np.array([value for value in display if value is not None], dtype=float)
    confident_points = sum(
        value is not None and confidence is not None and confidence >= RELIABLE_CONFIDENCE
        for value, confidence in zip(display, display_confidence)
    )
    voiced_percentage = round(len(voiced_values) / max(1, len(display)) * 100.0, 1)
    confident_voiced_percentage = round(confident_points / max(1, len(display)) * 100.0, 1)
    clipping_percentage = round(float(np.mean(np.abs(y) >= 0.999)) * 100.0, 3)
    rms_dbfs = round(20.0 * math.log10(max(float(np.sqrt(np.mean(np.square(y)))), 1e-9)), 1)
    flags: list[str] = []
    if confident_points < 20 or confident_voiced_percentage < 3.0:
        flags.append("low_pitch_confidence")
    if voiced_percentage < 10:
        flags.append("low_voiced_coverage")
    if clipping_percentage > 0.1:
        flags.append("clipping_detected")
    if rms_dbfs < -40:
        flags.append("low_signal_level")
    if len(voiced_values) < 20 or voiced_percentage < 3:
        raise PitchTrackError("no_reliable_pitch: too few confident sung-pitch frames were detected")
    low, high = np.percentile(voiced_values, [2.5, 97.5])
    return {
        "duration_seconds": round(duration_seconds, 3),
        "contour": {
            "rate_hz": DISPLAY_RATE_HZ,
            "units": "cents_rel_A440",
            "values": display,
            "confidence": display_confidence,
            "low_confidence": display_low_confidence,
        },
        "diagnostic_contour": {
            "rate_hz": RAW_RATE_HZ,
            "units": "cents_rel_A440",
            "values": raw,
            "confidence": raw_confidence,
            "low_confidence": raw_low_confidence,
        },
        "robust_min_note": note_from_cents(float(low)),
        "robust_max_note": note_from_cents(float(high)),
        "voiced_percentage": voiced_percentage,
        "quality": {
            "classification": "caution" if flags else "reliable",
            "flags": flags,
            "clipping_percentage": clipping_percentage,
            "rms_dbfs": rms_dbfs,
            "minimum_confidence": RELIABLE_CONFIDENCE,
            "confident_voiced_percentage": confident_voiced_percentage,
            "display_method": "voxai_canonical_pyin_contour",
        },
    }


def analyze(
    input_path: Path,
    job_dir: Path,
    performer_name: str = "Singer",
    song_name: str = "",
    original_artist: str = "",
    recording_conditions: str = "",
    stage_file: Path | None = None,
    comparison_enabled: bool = True,
    export_spectral_enabled: bool = False,
    analysis_deadline: float | None = None,
) -> dict:
    job_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(input_path)
    wav_path = job_dir / "analysis.wav"
    _write_stage(stage_file, "separating_vocals")
    vocals_path, instrumental_path = separate_stems(input_path, job_dir)
    _write_stage(stage_file, "preparing_audio")
    vocal_playback = job_dir / "vocals.mp3"
    instrumental_playback = job_dir / "instrumental.mp3"
    _run(["ffmpeg", "-y", "-i", str(vocals_path), "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(wav_path)], "conversion_failed")
    _run(["ffmpeg", "-y", "-i", str(vocals_path), "-vn", "-c:a", "libmp3lame", "-b:a", "160k", str(vocal_playback)], "conversion_failed")
    _run(["ffmpeg", "-y", "-i", str(instrumental_path), "-vn", "-c:a", "libmp3lame", "-b:a", "160k", str(instrumental_playback)], "conversion_failed")
    _write_stage(stage_file, "tracking_pitch")
    result = analyze_wav(wav_path, duration)
    _write_stage(stage_file, "running_v2_analysis")
    v2_analysis_file, v2_report_file = run_v2_analysis(wav_path, job_dir, performer_name)
    original_spectral_input = None
    pending_original_spectral_input = None
    result["stem_separation"] = {"enabled": True, "model": "UVR_MDXNET_Main"}
    result["audio_files"] = {"vocals": vocal_playback.name, "instrumental": instrumental_playback.name}
    result["v2_analysis_file"] = v2_analysis_file
    result["v2_report_file"] = v2_report_file
    result["metadata"] = {
        "performer_name": performer_name,
        "song_name": song_name,
        "original_artist": original_artist,
        "recording_conditions": recording_conditions,
        "comparison_enabled": comparison_enabled,
    }
    if comparison_enabled and song_name and original_artist:
        _write_stage(stage_file, "finding_original")
        try:
            reference_path, provenance = fetch_reference(song_name, original_artist, job_dir)
            _write_stage(stage_file, "analysing_original")
            original = analyze_original(
                reference_path,
                job_dir,
                original_artist,
                export_spectral_enabled=export_spectral_enabled,
            )
            pending_original_spectral_input = original.pop("_spectral_input", None)
            _write_stage(stage_file, "aligning_comparison")
            comparison, aligned_contour = compare_with_reference(
                job_dir / v2_analysis_file,
                job_dir / original["analysis_file"],
            )
            original_spectral_input = pending_original_spectral_input
            pending_original_spectral_input = None
            result["reference"] = {
                "status": "ready",
                "provenance": provenance,
                "contour": {
                    "rate_hz": result["contour"]["rate_hz"],
                    "units": "cents_rel_A440_aligned_to_singer_key_and_time",
                    "values": aligned_contour,
                },
                "native_contour": original["pitch"]["contour"],
                "quality": original["pitch"]["quality"],
                "robust_min_note": original["pitch"]["robust_min_note"],
                "robust_max_note": original["pitch"]["robust_max_note"],
                "analysis_file": original["analysis_file"],
            }
            result["comparison"] = comparison
        except PitchTrackError as exc:
            if pending_original_spectral_input is not None:
                _unlink_temporary_audio(
                    pending_original_spectral_input["wav_path"]
                )
            result["reference"] = {"status": "unavailable", "error": str(exc).split(":", 1)[-1].strip()}
    elif not comparison_enabled:
        result["reference"] = {"status": "skipped", "reason": "single_track_mode"}

    # Optional display artifacts run last, after every score and comparison is
    # complete. Each child is independently bounded by both its exporter cap
    # and the outer job deadline, with a publication/cleanup reserve.
    vocal_spectral = _maybe_export_spectral(
        export_spectral_enabled,
        wav_path,
        job_dir / "spectral" / "vocals",
        job_dir,
        result["contour"],
        "vocals",
        analysis_deadline,
    )
    if vocal_spectral is not None:
        sources = {"vocals": vocal_spectral}
        if original_spectral_input is not None:
            original_spectral = _maybe_export_spectral(
                True,
                original_spectral_input["wav_path"],
                job_dir / "spectral" / "original",
                job_dir,
                original_spectral_input["contour"],
                "original",
                analysis_deadline,
            )
            sources["original"] = original_spectral
        source_statuses = {source["status"] for source in sources.values()}
        result["spectral"] = {
            "version": "voxai_spectral_v1",
            "status": (
                "ready" if source_statuses == {"ready"} else
                "partial" if "ready" in source_statuses else
                "unavailable"
            ),
            "sources": sources,
        }
    _write_stage(stage_file, "building_report")
    (job_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    _unlink_temporary_audio(wav_path)
    if original_spectral_input is not None:
        _unlink_temporary_audio(original_spectral_input["wav_path"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--name", default="Singer")
    parser.add_argument("--song", default="")
    parser.add_argument("--artist", default="")
    parser.add_argument("--conditions", default="")
    parser.add_argument("--stage-file", type=Path)
    parser.add_argument("--skip-comparison", action="store_true")
    parser.add_argument("--export-spectral", action="store_true")
    parser.add_argument("--analysis-deadline-monotonic", type=float)
    args = parser.parse_args()
    try:
        analyze(
            args.input_file.resolve(),
            args.job_dir.resolve(),
            performer_name=args.name.strip() or "Singer",
            song_name=args.song.strip(),
            original_artist=args.artist.strip(),
            recording_conditions=args.conditions.strip(),
            stage_file=args.stage_file.resolve() if args.stage_file else None,
            comparison_enabled=not args.skip_comparison,
            export_spectral_enabled=args.export_spectral,
            analysis_deadline=args.analysis_deadline_monotonic,
        )
    except PitchTrackError as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
