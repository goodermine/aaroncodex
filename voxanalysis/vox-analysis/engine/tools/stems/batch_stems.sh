#!/usr/bin/env bash
set -euo pipefail

INPUT_PATH=""
OUTPUT_DIR=""
PYTHON_BIN="python3"
# MIT-licensed Mel-Band RoFormer (vocals) by Kimberley Jensen, via audio-
# separator. Chosen for commercial licensing: the previous UVR/MDX default
# weights are NOT commercially cleared (see docs/dependency-license-audit.md).
# RoFormer is heavier than MDX — prefer GPU for hosted use; override with
# --model for a lighter checkpoint if CPU speed demands it.
SEP_MODEL="vocals_mel_band_roformer.ckpt"
VENV_PATH="${HOME}/.venvs/vox-sep-uvr"

usage() {
  cat <<'EOF'
VOXAI stem-separation runner (vocals + instrumental).

Usage:
  batch_stems.sh --input <file-or-dir> --output <dir> [options]

Required:
  --input <path>      Input audio file or directory
  --output <dir>      Output directory for separated stems

Options:
  --python <bin>      Python binary (default: python3)
  --model <name>      audio-separator model name (default: vocals_mel_band_roformer.ckpt)
  --venv <path>       Dedicated venv path (default: ~/.venvs/vox-sep-uvr)
  --help              Show help

Examples:
  bash tools/stems/batch_stems.sh --input input/song.wav --output output/stems/song
  bash tools/stems/batch_stems.sh --input input/ --output output/stems/batch
EOF
}

log() { printf '[%s] %s\n' "$(date +'%H:%M:%S')" "$*"; }
err() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || err "Missing command: $1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      INPUT_PATH="$2"; shift 2 ;;
    --output)
      OUTPUT_DIR="$2"; shift 2 ;;
    --python)
      PYTHON_BIN="$2"; shift 2 ;;
    --model)
      SEP_MODEL="$2"; shift 2 ;;
    --venv)
      VENV_PATH="$2"; shift 2 ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      err "Unknown argument: $1" ;;
  esac
done

[[ -n "$INPUT_PATH" ]] || { usage; err "--input is required"; }
[[ -n "$OUTPUT_DIR" ]] || { usage; err "--output is required"; }

need_cmd "$PYTHON_BIN"
need_cmd ffmpeg
mkdir -p "$OUTPUT_DIR"

collect_inputs() {
  local src="$1"
  if [[ -f "$src" ]]; then
    printf '%s\0' "$src"
    return
  fi

  if [[ ! -d "$src" ]]; then
    err "Input path not found: $src"
  fi

  find "$src" -maxdepth 1 -type f \( \
    -iname '*.wav' -o -iname '*.mp3' -o -iname '*.flac' -o -iname '*.m4a' -o \
    -iname '*.aac' -o -iname '*.ogg' -o -iname '*.wma' \
  \) -print0 | sort -z
}

setup_env() {
  if [[ ! -x "$VENV_PATH/bin/audio-separator" ]]; then
    log "Creating stem-separation venv: $VENV_PATH"
    "$PYTHON_BIN" -m venv "$VENV_PATH"
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip setuptools wheel
    pip install audio-separator onnxruntime
  else
    # shellcheck source=/dev/null
    source "$VENV_PATH/bin/activate"
  fi
}

run_file() {
  local file="$1"
  log "Separating: $file"
  audio-separator -m "$SEP_MODEL" --output_dir "$OUTPUT_DIR" "$file"
}

main() {
  local files=() f count=0

  while IFS= read -r -d '' f; do
    files+=("$f")
  done < <(collect_inputs "$INPUT_PATH")

  if [[ ${#files[@]} -eq 0 ]]; then
    err "No supported audio files found in input path"
  fi

  log "Files detected: ${#files[@]}"
  log "Model: $SEP_MODEL"
  log "Output dir: $OUTPUT_DIR"

  setup_env

  for f in "${files[@]}"; do
    run_file "$f"
    count=$((count + 1))
  done

  log "Completed: $count file(s)"
}

main
