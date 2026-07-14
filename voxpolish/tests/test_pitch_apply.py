"""Pitch rendering tests: the corrections must actually land, transparently."""

import numpy as np
import pytest

from test_pitch import SR, _gap, _tone
from voxpolish.stages import pitch

pytestmark = pytest.mark.skipif(
    not pitch.vocoder_available(), reason="pyworld not installed"
)


def _median_f0(x):
    _, f0, _ = pitch.track(x, SR)
    v = f0 > 0
    assert v.any()
    return float(np.median(f0[v]))


def test_flat_note_is_actually_sharpened():
    # A4 sung 40 cents flat; full strength, fast retune -> should land near A4.
    flat = 440.0 * 2 ** (-40 / 1200)
    x = _tone(flat, 1.2)
    report = pitch.analyze(x, SR, strength=1.0, retune_ms=40.0, key=(9, "minor"))
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])

    assert applied["applied"]
    before = _median_f0(x)
    after = _median_f0(tuned[0])
    dev_before = 1200 * np.log2(before / 440.0)
    dev_after = 1200 * np.log2(after / 440.0)
    assert abs(dev_before) > 30
    assert abs(dev_after) < 12, f"still {dev_after:+.1f} cents off after tuning"


def test_partial_strength_moves_partway():
    flat = 440.0 * 2 ** (-40 / 1200)
    x = _tone(flat, 1.2)
    report = pitch.analyze(x, SR, strength=0.5, retune_ms=40.0, key=(9, "minor"))
    tuned, _ = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    dev_after = 1200 * np.log2(_median_f0(tuned[0]) / 440.0)
    assert -32 < dev_after < -8, f"expected roughly half-corrected, got {dev_after:+.1f}"


def test_in_tune_audio_is_passthrough():
    """Transparency guarantee: nothing to fix => bit-identical output."""
    x = _tone(440.0, 1.0)
    report = pitch.analyze(x, SR, strength=0.5, key=(9, "minor"))
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    assert not applied["applied"]
    assert np.array_equal(tuned, np.atleast_2d(x))


def test_length_and_level_are_preserved():
    flat = 330.0 * 2 ** (30 / 1200)
    x = np.concatenate([_tone(flat, 0.8), _gap(0.3), _tone(flat, 0.6)])
    report = pitch.analyze(x, SR, strength=1.0, retune_ms=40.0, key=(4, "minor"))
    tuned, _ = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    assert tuned.shape[1] == len(x)
    rms_in = np.sqrt(np.mean(x**2))
    rms_out = np.sqrt(np.mean(tuned[0].astype(np.float64) ** 2))
    assert abs(20 * np.log10(rms_out / rms_in)) < 2.0, "level shifted audibly"


def test_vibrato_is_preserved():
    """The field verdict fix: correction shifts the note's CENTER, it never
    fights vibrato. Depth of a 5.5 Hz / 25-cent vibrato must survive tuning."""
    flat_center = 440.0 * 2 ** (-25 / 1200)
    x = _tone(flat_center, 1.5, vibrato_hz=5.5, vibrato_cents=25)
    report = pitch.analyze(x, SR, strength=1.0, retune_ms=60.0, key=(9, "minor"))
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    assert applied["applied"]

    def cents_series(sig):
        _, f0, _ = pitch.track(sig, SR)
        v = f0 > 0
        c = 1200 * np.log2(f0[v] / 440.0)
        return c[3:-3]  # steady part

    before, after = cents_series(x), cents_series(tuned[0])
    # Center moved toward the note...
    assert abs(np.median(after)) < abs(np.median(before)) - 10
    # ...but the vibrato depth is intact (not flattened by frame-chasing).
    assert np.std(after) > 0.6 * np.std(before), (
        f"vibrato crushed: {np.std(before):.1f} -> {np.std(after):.1f} cents"
    )


def test_untouched_passages_are_bit_identical():
    """Only corrected note spans are resynthesized: an in-tune phrase in the
    same take must come through byte-for-byte."""
    good = _tone(440.0, 0.8)
    flat = _tone(440.0 * 2 ** (-40 / 1200), 0.8)
    x = np.concatenate([good, _gap(0.4), flat, _gap(0.2)])
    report = pitch.analyze(x, SR, strength=1.0, key=(9, "minor"))
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    assert applied["applied"]
    n_good = int(0.85 * SR)  # the in-tune phrase plus a little margin
    assert np.array_equal(tuned[0, :n_good], x[:n_good].astype(np.float32))


def test_deadband_leaves_nearly_in_tune_notes_alone():
    """A note 8 cents off is a singer, not a problem: zero correction."""
    x = _tone(440.0 * 2 ** (-8 / 1200), 1.0)
    report = pitch.analyze(x, SR, strength=1.0, key=(9, "minor"))
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, report["curve"])
    assert not applied["applied"]
    assert np.array_equal(tuned, np.atleast_2d(x))


def test_unstable_spans_are_skipped_not_garbled():
    """Field garble fix (noisy source, 0:45-0:55): if the vocoder's own pitch
    track is unstable inside a corrected span, that span must be skipped —
    original audio wins over risky resynthesis."""
    rng = np.random.default_rng(5)
    flat = _tone(440.0 * 2 ** (-40 / 1200), 0.8)
    noise = (rng.standard_normal(int(0.8 * SR)) * 0.15).astype(np.float32)
    x = np.concatenate([flat, _gap(0.3), noise, _gap(0.2)])

    report = pitch.analyze(x, SR, strength=1.0, key=(9, "minor"))
    # Forge corrections over the unpitched noise, as a bad edit (or a bad
    # analysis on noisy material) would.
    noise_start = 1.1
    forged = report["curve"] + [
        [round(t, 3), 30.0] for t in np.arange(noise_start + 0.1, noise_start + 0.7, 0.03)
    ]
    tuned, applied = pitch.apply_correction(np.atleast_2d(x), SR, forged)

    assert applied["applied"]
    assert applied["skipped_unstable_spans"] >= 1, applied
    # The noise region is untouched, byte for byte.
    i0, i1 = int((noise_start + 0.05) * SR), int((noise_start + 0.75) * SR)
    assert np.array_equal(tuned[0, i0:i1], x[i0:i1])
    # And the legitimate flat note still got corrected.
    seg = slice(int(0.1 * SR), int(0.7 * SR))
    assert not np.array_equal(tuned[0, seg], x[seg])


def test_all_unstable_spans_means_passthrough():
    rng = np.random.default_rng(6)
    noise = (rng.standard_normal(int(1.2 * SR)) * 0.15).astype(np.float32)
    forged = [[round(t, 3), 30.0] for t in np.arange(0.1, 1.0, 0.03)]
    tuned, applied = pitch.apply_correction(np.atleast_2d(noise), SR, forged)
    assert not applied["applied"]
    assert np.array_equal(tuned, np.atleast_2d(noise))


def test_gaps_are_never_bridged():
    """Correction between two phrases must be zero — no interpolation across gaps."""
    flat = 440.0 * 2 ** (-40 / 1200)
    x = np.concatenate([_tone(flat, 0.6), _gap(0.5), _tone(440.0, 0.6)])
    report = pitch.analyze(x, SR, strength=1.0, key=(9, "minor"))
    # Sample the middle of the gap, clear of the tracker's frame-width smear
    # at the phrase edges (~frame/2 + the 50 ms mapping tolerance).
    t = np.arange(0.70, 1.02, 0.01)
    cents = pitch._dense_cents(t, report["curve"])
    assert np.all(cents == 0.0), "gap frames received correction"
