"""Remix balance contract: vocal trim in the sum only, headroom preserved."""

import numpy as np

from voxpolish.pipeline import REMIX_PEAK_CEILING_DB, Settings, mix_remix

SR = 44100


def _sine(freq, dur_s, amp):
    t = np.arange(int(dur_s * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)[None, :]


def test_song_mode_defaults_to_minus_2db_vocal_trim():
    assert Settings.for_mode("song").remix_vocal_db == -2.0
    assert Settings.for_mode("voice").remix_vocal_db == 0.0


def test_vocal_trim_scales_only_the_vocal():
    vocal = _sine(440, 1.0, 0.2)
    silence = np.zeros_like(vocal)
    remix = mix_remix(vocal, silence, vocal_trim_db=-2.0)
    assert np.allclose(remix, vocal * 10 ** (-2 / 20), atol=1e-7)

    # Instrumental passes through untouched when the vocal is silent.
    instr = _sine(220, 1.0, 0.2)
    remix = mix_remix(np.zeros_like(instr), instr, vocal_trim_db=-2.0)
    assert np.allclose(remix, instr, atol=1e-7)


def test_headroom_ceiling_scales_both_parts_equally():
    # In-phase sines force the sum over full scale.
    vocal = _sine(440, 0.5, 0.9)
    instr = _sine(440, 0.5, 0.9)
    remix = mix_remix(vocal, instr, vocal_trim_db=-2.0)

    ceiling = 10 ** (REMIX_PEAK_CEILING_DB / 20)
    peak = np.max(np.abs(remix))
    assert peak <= ceiling + 1e-6, "remix must respect the headroom ceiling"

    # Equal scaling: the normalized remix is an exact scalar multiple of the
    # trimmed sum, so the vocal-to-instrumental relationship is preserved.
    expected = vocal * 10 ** (-2 / 20) + instr
    scale = ceiling / np.max(np.abs(expected))
    assert np.allclose(remix, expected * scale, atol=1e-6)


def test_quiet_remix_is_never_scaled_up():
    vocal = _sine(440, 0.5, 0.05)
    instr = _sine(330, 0.5, 0.05)
    remix = mix_remix(vocal, instr, vocal_trim_db=0.0)
    assert np.allclose(remix, vocal + instr, atol=1e-7)
