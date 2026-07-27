"""Reference audio pairing — the calibration pack must not gain a wrong song.

The pack defines what "10" means for every score in the system, so a mispairing
(a remaster for an original, or a different song of the same length) shifts
every score with nothing to flag it afterwards. Duration alone is not enough:
Hot Chocolate's You Sexy Thing and Donna Summer's On The Radio are 0.4s apart.

Every case below is a real pairing or a real near-collision from Aaron's
reference folder.
"""

from __future__ import annotations

import importlib.util
import os


def _repo_root(start):
    path = start
    while path != os.path.dirname(path):
        if os.path.isfile(os.path.join(path, "CLAUDE.md")):
            return path
        path = os.path.dirname(path)
    raise RuntimeError("repo root not found")


ROOT = _repo_root(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "pair_reference_audio", os.path.join(ROOT, "tools/pair_reference_audio.py"))
PAIR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PAIR)


def agree(ref, cand):
    return PAIR.names_agree(PAIR.norm_tokens(ref), PAIR.norm_tokens(cand))


TRUE_PAIRS = [
    # source titled with the SONG ONLY — the artist never appears
    ("alan-jackson-chasin-that-neon-rainbow", "Chasin_That_Neon_Rainbow___qFacDXU6qM.mp3"),
    ("andy-gibb-i-just-want-to-be-your-everything", "I_Just_Want_To_Be_Your_Everything__d3JbAM40Uv4.mp3"),
    ("donna-summer-on-the-radio", "On_The_Radio__qqi-8nv5ngk.mp3"),
    ("carpenters-this-masquerade-reference", "This_Masquerade [1f-R9R-3YoE].mp3"),
    # apostrophes split unevenly across the two naming styles
    ("marvin-gaye-lets-get-it-on", "Let_s_Get_It_On__tQj1kPmQXwE.mp3"),
    ("john-farnham-youre-the-voice", "John Farnham - You're the Voice__tbkOZTSvrHs.mp3"),
    ("tina-turner-whats-love-got-to-do-with-it",
     "Tina_Turner_-_What_s_Love_Got_To_Do_With_It_Official_Video_HD__oGpFcHTxjZs.mp3"),
    # single-word title
    ("kryptonite-3-doors-down-reference", "Kryptonite [NtBwVWWa3Ss].mp3"),
    # download ids in brackets and after a double underscore
    ("michael-buble-feeling-good-reference", "Feeling_Good [Gtla5Bc9kjk].mp3"),
    ("aerosmith-dream-on", "Aerosmith_-_Dream_On_Audio__89dGC8de0CA.mp3"),
    ("adele-rolling-in-the-deep", "Adele_-_Rolling_in_the_Deep_Official_Music_Video__rYEDA3JcQqw.mp3"),
    ("gordon-lightfoot-if-you-could-read-my-mind-reference",
     "Gordon_Lightfoot_-_If_You_Could_Read_My_Mind [v5tr_L31StI].mp3"),
    ("joe-cocker-the-letter-reference", "The_Letter_Single_Version [rY4MrmZWiAk].mp3"),
    ("hozier-take-me-to-church", "Hozier - Take Me To Church__PVjiKRfKpPI.mp3"),
    # uuid-suffixed reference naming
    ("Bon_Jovi_-_Livin_On_A_Prayer_lDK9QqIzhwk_1---33c3d53e", "Bon Jovi - Livin On A Prayer.webm"),
]

ACCENTED = [
    # The stored reference name transliterates the accent to a separator, so
    # "Céline" is held as "Ce_line" -> {ce, line} while any download has {celine}.
    ("Ce_line_Dion_My_Heart_Will_Go_On_Official_Audio_mNsm2P0l_7Y---97672687",
     "Celine_Dion_-_My_Heart_Will_Go_On_Official_Audio__mNsm2P0l7Y.mp3"),
    ("Ce_line_Dion_My_Heart_Will_Go_On", "Celine Dion - My Heart Will Go On.mp3"),
]


TRAPS = [
    # Dimash covers the SAME SONG as the Celine reference. Rejoining the split
    # name must not make every My Heart Will Go On interchangeable.
    ("Ce_line_Dion_My_Heart_Will_Go_On_Official_Audio_mNsm2P0l_7Y---97672687",
     "Incredible_performance_of_Titanic_My_heart_will_go_on_by_DIMASH.mp3"),
    # 244.98s vs 244.6s — different songs, would have entered the pack
    ("Hot_Chocolate-_You_Sexy_Thing_original_YUY9Y9RFiHY", "On_The_Radio__qqi-8nv5ngk.mp3"),
    # 302.35s vs 300.7s
    ("wild-cherry-play-that-funky-music-reference",
     "George_Michael_-_Careless_Whisper_Official_Video__izGwDsrQ1eQ.mp3"),
    # a single shared common word is not evidence
    ("alan-jackson-chasin-that-neon-rainbow", "One_Single_Version [BvA5xFuDb0o].mp3"),
    ("beyonce-halo", "Glenn_Frey_-_1984_-_The_Heat_Is_On [_LVS0UdkFMQ].mp3"),
    ("Mariah_Carey_-_Vision_Of_Love_tov22NtCMC4",
     "Sam Smith - Stay With Me (Official Music Video)__pB-5XG-DbAA.mp3"),
    ("Bon_Jovi_-_Livin_On_A_Prayer_lDK9QqIzhwk_1",
     "Journey_-_Don_t_Stop_Believin_Official_Audio__1k8craCGpgs.mp3"),
    ("donna-summer-on-the-radio", "Kryptonite [NtBwVWWa3Ss].mp3"),
    ("marvin-gaye-lets-get-it-on", "This_Masquerade [1f-R9R-3YoE].mp3"),
    ("idina-menzel-let-it-go", "Beyonce_-_Halo__bnVUHWCynig.mp3"),
    ("teddy-swims-lose-control", "Alicia_Keys_-_If_I_Ain_t_Got_You_Official_HD_Video__Ju8Hr50Ckwk.mp3"),
]


def test_transliterated_accents_still_pair():
    """Renaming the source file would hide this and it would recur on the next
    accented artist."""
    missed = [(r, c) for r, c in ACCENTED if not agree(r, c)]
    assert not missed, f"failed to pair across a transliterated accent: {missed}"


def test_real_pairs_are_matched():
    missed = [(r, c) for r, c in TRUE_PAIRS if not agree(r, c)]
    assert not missed, f"failed to pair: {missed}"


def test_wrong_songs_are_never_matched():
    """These all pass the duration test. Name agreement is the only thing
    standing between them and the calibration pack."""
    wrong = [(r, c) for r, c in TRAPS if agree(r, c)]
    assert not wrong, f"would have mispaired: {wrong}"


def test_separator_words_are_not_treated_as_song_words():
    """Reading tokens from the stem filename made every reference carry
    vocals/uvr/mdxnet/main, and matched 0 of 50."""
    assert PAIR.norm_tokens("adele-rolling-in-the-deep_(Vocals)_UVR_MDXNET_Main.flac") \
        == PAIR.norm_tokens("adele-rolling-in-the-deep")
