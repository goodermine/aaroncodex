#!/usr/bin/env python3
"""Catch a professional original mislabeled as a singer's own take.

The Andy Gibb "I Just Want To Be Your Everything" original was dropped into
Aaron's uploads under an `aaron-` filename and scored 9.2 — briefly his best
take, and never him. Aaron caught it by ear; nothing in the pipeline did.

The screen: a singer take whose SONG matches a reference original AND whose
duration matches it to within a fraction of a second. Same song is required, not
duration alone — 3-4 minute pop songs cluster around similar lengths, so
duration-only flags dozens of coincidences between DIFFERENT songs. Requiring the
titles to agree removes those (on the archive that surfaced this, 27 duration
collisions collapsed to 1 once same-song was required).

It SCREENS, it does not decide, and it never auto-blocks. A karaoke cover sung
over the original-length backing track legitimately matches the original's
duration closely — Aaron's real Heat Is On and Danger Zone covers land 0.5-1.5 s
from their originals. So a close match is a prompt to LISTEN, not proof. The Andy
Gibb mislabel matched at 0.02 s and was confirmed by ear; the human is the ground
truth, as that whole episode showed. Run it after any archive change:

    python3 tools/check_take_integrity.py
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "voxanalysis/archive/scratch-analyses")
REFS = os.path.join(ROOT, "voxanalysis/vox-analysis/engine/calibration/references")

# Reuse the name matcher already hardened against artist-omitted, accented and
# id-suffixed filenames — the same logic that paired 50 reference sources.
sys.path.insert(0, os.path.join(ROOT, "tools"))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "pair_reference_audio", os.path.join(ROOT, "tools/pair_reference_audio.py"))
_pair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pair)

# A cover cannot match the original's length this tightly. Sub-second same-song
# agreement means the same audio.
# A karaoke cover sung over the original-length backing track CAN match the
# original's duration to within ~0.5-1.5s (observed on Aaron's real Heat Is On
# and Danger Zone covers). So duration alone cannot prove a mislabel and this
# tool never auto-blocks — it SCREENS, and a human confirms by ear, which is how
# the Andy Gibb case was actually resolved. The tight band below is where a match
# is close enough to be worth a listen; the Andy Gibb original matched at 0.02s.
CONFIRM_S = 0.25
SINGERS = ("aaron-g", "aaron", "rilda", "chris", "leo")


def _is_singer_take(name: str) -> bool:
    import re as _re
    low = name.lower()
    return any(_re.search(rf"(?:^|-){_re.escape(t)}-", low) for t in SINGERS)


def _song_tokens(take_name: str) -> set[str]:
    s = re.sub(r"^20\d\d-\d\d-\d\d-", "", take_name)
    s = re.sub(r"^(aaron-g-|aaron-|rilda-|chris-|leo-)", "", s)
    s = re.sub(r"-take-\d+.*$", "", s)
    s = re.sub(r"-20\d\d.*$", "", s)
    return _pair.norm_tokens(s)


def scan(archive_dir: str = ARCHIVE, refs_dir: str = REFS) -> list[dict]:
    """Return suspected mislabels, worst (tightest duration) first."""
    refs = []
    for p in sorted(glob.glob(os.path.join(refs_dir, "*_analysis.json"))):
        try:
            d = json.load(open(p))
        except (OSError, json.JSONDecodeError):
            continue
        refs.append((os.path.basename(p).replace("_analysis.json", ""),
                     d.get("duration_seconds"),
                     _pair.norm_tokens(os.path.basename(p))))

    suspects = []
    for p in sorted(glob.glob(os.path.join(archive_dir, "*_analysis.json"))):
        try:
            d = json.load(open(p))
        except (OSError, json.JSONDecodeError):
            continue
        name = os.path.basename(p).replace("_analysis.json", "")
        if not _is_singer_take(name):     # reference duplicates are not takes
            continue
        dur = d.get("duration_seconds")
        if dur is None:
            continue
        stok = _song_tokens(name)
        for rname, rdur, rtok in refs:
            if rdur is None:
                continue
            gap = abs(dur - rdur)
            if gap <= CONFIRM_S and _pair.names_agree(stok, rtok):
                suspects.append({
                    "take": name, "take_duration_s": dur,
                    "reference": rname, "reference_duration_s": rdur,
                    "gap_s": round(gap, 3),
                })
    return sorted(suspects, key=lambda s: s["gap_s"])


def main() -> int:
    suspects = scan()
    if not suspects:
        print("ok    no singer take is a near-exact duration match to a reference original")
        return 0
    print("CONFIRM BY EAR — these takes match a reference original's song AND duration")
    print("very closely. A karaoke cover CAN do this, so this is not proof — but the")
    print("Andy Gibb original that was mislabeled as Aaron's take matched at 0.02s.\n")
    for x in suspects:
        print(f"  {x['gap_s']}s apart  {x['take']}")
        print(f"             vs original {x['reference']} ({x['reference_duration_s']}s)")
    print("\nCheck each against the singer. If it is the original, move it out of")
    print("voxanalysis/archive/scratch-analyses/ and re-score. Advisory only — not blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
