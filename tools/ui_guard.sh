#!/usr/bin/env bash
# ============================================================================
# UI quality gates (Phase 1 of the light redesign — docs/plans/UI_REDESIGN_AUDIT.md)
#
#   1. One source of colour truth: no hex / rgb() outside vox-tokens.css
#   2. No dark-mode remnants: no data-theme, prefers-color-scheme, vox-theme
#   3. Zero vendor drift: every synced file identical to its /design canonical
#   4. WCAG AA contrast on every token text pair (tools/check_contrast.py)
#
# Exit 0 = all gates green. Any failure prints and exits 1.
# ============================================================================
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
fail=0

# Shipped UI surfaces under the gate. NOT yet included (tracked debt):
#   voxanalysis/vox-analysis/viewer/static/index.html  — legacy page, retired in Phase 2
#   pitchmonitor/                                       — rebuilt on the kit in Phase 4
#   design/vox-suite-concept.html, design/vox-suite-spec.html — dark-era design archives
#   design/next/                                        — Phase-0 static mockups
SCOPE=(
  design/vox-kit.css design/vox-record.css design/vox-report.css
  design/vox-record.js design/vox-report.js design/vox-about.js design/vox-telemetry.js
  voxsuite/src/voxsuite/server/static/deck.html
  voxsuite/src/voxsuite/server/buildpage.py
  voxanalysis/vox-analysis/viewer/static/deck.html
  voxpolish/src/voxpolish/server/static/deck.html
  voxpolish/src/voxpolish/server/static/index.html
)

echo "== gate 1: no colour definitions outside vox-tokens.css =="
# strip HTML entities (&#9654;) and theme-color meta (browser meta cannot use var())
hits=$(grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(\s*[0-9.]' "${SCOPE[@]}" 2>/dev/null \
       | sed -E 's/&#[0-9]+;//g' \
       | grep -vE 'name="theme-color"' \
       | grep -E '#[0-9a-fA-F]{3,8}\b|rgba?\(\s*[0-9.]' )
if [ -n "$hits" ]; then
  echo "$hits" | head -30
  echo "FAIL: colours found outside design/vox-tokens.css"; fail=1
else
  echo "ok"
fi

echo "== gate 2: no dark-mode remnants =="
hits=$(grep -nE 'data-theme|prefers-color-scheme|vox-theme' "${SCOPE[@]}" design/sync.sh 2>/dev/null)
if [ -n "$hits" ]; then
  echo "$hits" | head -20
  echo "FAIL: dark-mode remnants found"; fail=1
else
  echo "ok"
fi

echo "== gate 3: zero vendor drift =="
files=(vox-tokens.css vox-kit.css vox-telemetry.js vox-about.js vox-report.js vox-report.css vox-record.js vox-record.css site.webmanifest)
targets=(voxpolish/src/voxpolish/server/static voxanalysis/vox-analysis/viewer/static voxsuite/src/voxsuite/server/static)
drift=0
for t in "${targets[@]}"; do
  for f in "${files[@]}"; do
    if [ -f "$t/$f" ] && ! cmp -s "design/$f" "$t/$f"; then
      echo "DRIFT: $t/$f != design/$f"; drift=1
    fi
  done
done
if [ "$drift" -eq 1 ]; then echo "FAIL: run design/sync.sh"; fail=1; else echo "ok"; fi

echo "== gate 4: WCAG AA contrast on token pairs =="
python3 tools/check_contrast.py || fail=1

if [ "$fail" -eq 0 ]; then
  echo; echo "UI GUARD PASSED — all gates green."
else
  echo; echo "UI GUARD FAILED — fix the gates above before shipping UI."
fi
exit $fail
