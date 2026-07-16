#!/usr/bin/env bash
# Vendor the canonical VOX design layer into each app's static directory.
# Canonical source is /design; edit there, then run this to propagate.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"

files=(vox-tokens.css vox-kit.css vox-telemetry.js vox-about.js vox-report.js vox-report.css vox-record.js vox-record.css)

targets=(
  "$root/voxpolish/src/voxpolish/server/static"
  "$root/voxanalysis/vox-analysis/viewer/static"
  "$root/voxsuite/src/voxsuite/server/static"
)

for target in "${targets[@]}"; do
  if [[ -d "$target" ]]; then
    for f in "${files[@]}"; do
      cp "$here/$f" "$target/$f"
      echo "synced $f -> ${target#"$root"/}/$f"
    done
  else
    echo "skip (not found): ${target#"$root"/}"
  fi
done

echo "done."
