"""Regression tests for song() in rescore_all.py -- the grouping key behind
"songs sung more than once". See the comment above song() for the two bugs
this closes: take-number fragmentation and venue/capture-tag fragmentation.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rescore_all", os.path.join(HERE, "rescore_all.py"))
rescore_all = importlib.util.module_from_spec(spec)
sys.modules["rescore_all"] = rescore_all
spec.loader.exec_module(rescore_all)   # module-level defs only now; main() is guarded
song = rescore_all.song


class SongGroupingTests(unittest.TestCase):
    def test_same_song_different_take_numbers_group_together(self):
        """Take number resets per session, so it must not split one song into
        several single-take groups (Kung Fu Fighting was fragmented into 9)."""
        self.assertEqual(
            song("2026-08-01-aaron-kung-fu-fighting-take-004"),
            song("2026-09-12-aaron-kung-fu-fighting-take-001"),
        )

    def test_venue_and_capture_tags_strip_to_the_same_song(self):
        cases = [
            ("2026-07-11-aaron-kryptonite-mango-hill-tavern-take-001",
             "2026-07-10-aaron-kryptonite-take-002"),
            ("2026-07-25-aaron-pressure-down-captain-cook-tavern-take-001",
             "2026-07-24-aaron-pressure-down-take-001"),
            ("2026-08-27-aaron-reasons-zoom-h8-capture-take-004",
             "2026-07-29-aaron-reasons-take-001"),
            ("2026-08-29-aaron-to-be-with-you-zoom-h8-capture-take-001",
             "2026-08-22-aaron-to-be-with-you-take-001"),
            ("2026-07-11-aaron-danger-zone-new-studio-take-002",
             "2026-07-10-aaron-danger-zone-take-001"),
            ("2026-09-15-aaron-all-that-she-wants-home-instamic-take-002",
             "2026-09-11-aaron-all-that-she-wants-take-001"),
        ]
        for tagged, plain in cases:
            self.assertEqual(song(tagged), song(plain), f"{tagged} vs {plain}")

    def test_apostrophe_dropped_vs_hyphenated_group_together(self):
        self.assertEqual(
            song("2026-07-11-aaron-lets-stay-together-new-studio-take-001"),
            song("2026-07-02-aaron-let-s-stay-together-take-001"),
        )

    def test_descriptor_stripping_never_eats_a_real_song_title_word(self):
        """'bay' is a whole word inside a real title here (Blue Bayou), not a
        venue tag -- a substring strip (instead of whole-segment) would wrongly
        truncate it. 'live' is a real archived song title elsewhere (Alex --
        Live It Up), which is why 'live' was deliberately left out of
        DESCRIPTOR_SUFFIXES rather than added for the (unrelated) session-order
        note."""
        self.assertEqual(song("2026-06-25-rilda-blue-bayou-take-001"), "blue-bayou")
        self.assertEqual(song("2026-07-29-aaron-live-it-up-take-001"), "live-it-up")

    def test_different_songs_never_collide(self):
        self.assertNotEqual(
            song("2026-07-04-aaron-the-letter-take-001"),
            song("2026-07-10-aaron-the-heat-is-on-take-001"),
        )
        self.assertNotEqual(
            song("2026-07-02-aaron-let-s-stay-together-take-001"),
            song("2026-08-31-aaron-let-s-go-take-001"),
        )


if __name__ == "__main__":
    unittest.main()
