from __future__ import annotations

import os
import platform
import subprocess
import time
import traceback
from pathlib import Path
from typing import Dict, List
from wave import open as wave_open

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from ..models import EngineMetadata, SeparationRequest, SeparationResponse, StemArtifact
from .files import ensure_existing_file, ensure_output_dir, ensure_within_dir

try:
    from importlib.metadata import version as package_version
except ImportError:  # pragma: no cover
    from importlib_metadata import version as package_version


DEFAULT_MODEL = "UVR_MDXNET_Main.onnx"
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
_PATCHED_COMMON_SEPARATOR = False


def read_wav_metadata(path: Path) -> Dict[str, float | int | None]:
    try:
        with wave_open(str(path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frame_count = wav_file.getnframes()
            duration = frame_count / sample_rate if sample_rate else None
            return {
                "sampleRate": sample_rate,
                "channels": channels,
                "durationSec": duration,
            }
    except Exception:
        return {
            "sampleRate": None,
            "channels": None,
            "durationSec": None,
        }


def _normalize_stem_name(file_path: Path) -> str:
    stem_name = file_path.stem.lower()
    if "vocal" in stem_name:
        return "vocals"
    if "instrumental" in stem_name or "other" in stem_name:
        return "instrumental"
    return stem_name


def _list_output_files(output_dir: Path) -> List[str]:
    if not output_dir.exists():
        return []
    return sorted(str(path.resolve()) for path in output_dir.rglob("*") if path.is_file())


def _log_runtime_context() -> None:
    ffmpeg_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
    ffmpeg_banner = ffmpeg_result.stdout.splitlines()[0] if ffmpeg_result.returncode == 0 and ffmpeg_result.stdout else "ffmpeg unavailable"
    print(
        "[vox-separate] runtime",
        {
            "python": platform.python_version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "ffmpeg": ffmpeg_banner,
            "numba_disable_jit": os.environ.get("NUMBA_DISABLE_JIT"),
        },
    )


def patch_common_separator() -> None:
    global _PATCHED_COMMON_SEPARATOR
    if _PATCHED_COMMON_SEPARATOR:
        return

    from audio_separator.separator.common_separator import CommonSeparator

    def resample_channel(channel: np.ndarray, original_sr: int, target_sr: int) -> np.ndarray:
        if original_sr == target_sr:
            return channel.astype(np.float32, copy=False)

        from math import gcd

        factor = gcd(original_sr, target_sr)
        up = target_sr // factor
        down = original_sr // factor
        return resample_poly(channel, up, down).astype(np.float32, copy=False)

    def prepare_mix_safe(self, mix):
        audio_path = mix

        if not isinstance(mix, np.ndarray):
            self.logger.debug(f"[vox-patch] Loading audio with soundfile from file: {mix}")
            try:
                audio_info = sf.info(mix)
                self.input_subtype = audio_info.subtype

                if "PCM_16" in self.input_subtype or self.input_subtype == "PCM_S8":
                    self.input_bit_depth = 16
                elif "PCM_24" in self.input_subtype:
                    self.input_bit_depth = 24
                elif "PCM_32" in self.input_subtype or "FLOAT" in self.input_subtype or "DOUBLE" in self.input_subtype:
                    self.input_bit_depth = 32
                else:
                    self.input_bit_depth = 16
                    self.logger.warning(f"[vox-patch] Unknown audio subtype {self.input_subtype}, defaulting to 16-bit output")

                self.logger.info(f"[vox-patch] Input audio subtype: {self.input_subtype}")
                self.logger.info(f"[vox-patch] Detected input bit depth: {self.input_bit_depth}-bit")
            except Exception as exc:
                self.logger.warning(f"[vox-patch] Could not read audio file info, defaulting to 16-bit output: {exc}")
                self.input_bit_depth = 16
                self.input_subtype = "PCM_16"

            mix, sr = sf.read(mix, always_2d=True, dtype="float32")
            self.logger.info(f"[vox-patch] Soundfile loaded audio at {sr} Hz with shape {mix.shape}")
            mix = mix.T

            if sr != self.sample_rate:
                self.logger.info(f"[vox-patch] Resampling from {sr} Hz to {self.sample_rate} Hz")
                mix = np.vstack([resample_channel(channel, sr, self.sample_rate) for channel in mix]).astype(np.float32)
        else:
            self.logger.debug("[vox-patch] Using provided ndarray mix")
            if self.input_bit_depth is None:
                self.input_bit_depth = 16
                self.input_subtype = "PCM_16"
            mix = mix.T

        if isinstance(audio_path, str) and not np.any(mix):
            raise ValueError(f"Audio file {audio_path} is empty or not valid")

        if mix.ndim == 1:
            mix = np.asfortranarray([mix, mix])
        elif mix.shape[0] == 1:
            mix = np.vstack([mix, mix])

        self.logger.info(f"[vox-patch] Prepared mix shape: {mix.shape}")
        return mix

    def write_audio_safe(self, stem_path: str, stem_source):
        samples = stem_source.shape[0] if getattr(stem_source, "ndim", 0) >= 1 else 0
        duration_seconds = samples / self.sample_rate if self.sample_rate else 0
        duration_hours = duration_seconds / 3600 if duration_seconds else 0
        self.logger.info(f"[vox-patch] Audio duration is {duration_hours:.2f} hours ({duration_seconds:.2f} seconds).")

        if self.use_soundfile:
            self.logger.warning("[vox-patch] Using soundfile for writing.")
            self.write_audio_soundfile(stem_path, stem_source)
        else:
            self.logger.info("[vox-patch] Using pydub for writing.")
            self.write_audio_pydub(stem_path, stem_source)

    CommonSeparator.prepare_mix = prepare_mix_safe
    CommonSeparator.write_audio = write_audio_safe
    _PATCHED_COMMON_SEPARATOR = True


def run_separation(request: SeparationRequest) -> SeparationResponse:
    from audio_separator.separator import Separator

    patch_common_separator()
    _log_runtime_context()

    input_path = ensure_existing_file(request.inputPath)
    output_dir = ensure_output_dir(request.outputDir)
    warnings: List[str] = []
    stage_times = {}

    model_filename = request.modelFilename or DEFAULT_MODEL
    print(
        "[vox-separate] request",
        {
            "jobId": request.jobId,
            "inputPath": str(input_path),
            "outputDir": str(output_dir),
            "modelFilename": model_filename,
            "preExistingFiles": _list_output_files(output_dir),
        },
    )

    init_start = time.perf_counter()
    separator = Separator(
        output_dir=str(output_dir),
        output_format="WAV",
    )
    stage_times["separatorInitSec"] = round(time.perf_counter() - init_start, 3)

    load_start = time.perf_counter()
    separator.load_model(model_filename=model_filename)
    stage_times["modelLoadSec"] = round(time.perf_counter() - load_start, 3)
    model_instance = separator.model_instance

    print(
        "[vox-separate] model",
        {
            "jobId": request.jobId,
            "modelClass": type(model_instance).__name__ if model_instance is not None else None,
            "torchDevice": str(getattr(separator, "torch_device", None)),
            "sampleRate": getattr(model_instance, "sample_rate", None),
            "outputDir": getattr(model_instance, "output_dir", None),
        },
    )

    output_names = {
        "Vocals": "vocals",
        "Instrumental": "instrumental",
    }

    separate_start = time.perf_counter()
    try:
        output_files = separator._separate_file(str(input_path), output_names)
    except Exception as exc:
        existing_files = _list_output_files(output_dir)
        message = (
            f"Separation failed during model execution. "
            f"model={model_filename}; modelClass={type(model_instance).__name__ if model_instance is not None else 'unknown'}; "
            f"input={input_path}; outputDir={output_dir}; filesAfterRun={existing_files}; "
            f"error={exc!r}; traceback={traceback.format_exc(limit=8)}"
        )
        raise RuntimeError(message) from exc

    stage_times["separateSec"] = round(time.perf_counter() - separate_start, 3)
    actual_files = _list_output_files(output_dir)
    print(
        "[vox-separate] result",
        {
            "jobId": request.jobId,
            "returnedOutputFiles": output_files,
            "filesPresent": actual_files,
            "stageTimes": stage_times,
        },
    )

    if not output_files and actual_files:
        warnings.append("Separator returned no output paths, but files were present on disk. Using discovered files from output directory.")
        output_files = actual_files

    if not output_files:
        raise RuntimeError(
            f"python-audio-separator returned no output files. "
            f"model={model_filename}; modelClass={type(model_instance).__name__ if model_instance is not None else 'unknown'}; "
            f"filesPresent={actual_files}; stageTimes={stage_times}"
        )

    outputs = {}
    for output_file in output_files:
        candidate_path = Path(output_file)
        if not candidate_path.is_absolute():
            candidate_path = output_dir / candidate_path
        resolved_path = ensure_within_dir(candidate_path, output_dir)
        stem_key = _normalize_stem_name(resolved_path)
        metadata = read_wav_metadata(resolved_path)
        outputs[stem_key] = StemArtifact(
            path=str(resolved_path),
            format=resolved_path.suffix.lstrip(".").lower() or "wav",
            sampleRate=metadata["sampleRate"],
            channels=metadata["channels"],
            durationSec=metadata["durationSec"],
        )

    if "vocals" not in outputs:
        warnings.append("Separator completed but no vocals stem was identified in the output file names.")
    if "instrumental" not in outputs:
        warnings.append("Separator completed but no instrumental stem was identified in the output file names.")

    return SeparationResponse(
        ok=True,
        jobId=request.jobId,
        engine=EngineMetadata(
            name="python-audio-separator",
            version=package_version("audio-separator"),
            model=model_filename,
        ),
        outputs=outputs,
        warnings=warnings,
    )
