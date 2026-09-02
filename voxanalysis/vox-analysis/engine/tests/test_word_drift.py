"""WORDS vs NOTES — the diagnostic that splits held-note drift into the vowel
wandering versus the pitch being knocked off at a consonant/word boundary.

Built 2 Sep 2026 for a specific coaching question: Aaron lands the pitch on the
first word of a line and it moves as the words change underneath it. Whole-note
drift cannot tell that apart from a vowel that slides. This can, per note, with
timestamps — and it is a diagnostic: never scored, and outside the measurement
fingerprint so adding it moved no provenance.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyse_song as A  # noqa: E402

SR, HOP = 44100, 512


def _synth(notes, gap_s=0.4):
    """Build (y, f0) for a sequence of notes. Each note: (hz, seconds, dips)
    where dips is a list of (at_s, dip_amp, pitch_cents) — a smooth (Hann)
    energy dip to `dip_amp` of full level over 100 ms, with the pitch pushed by
    up to `pitch_cents` over a 120 ms bump around it — a consonant-shaped knock,
    not a step (a step would be a new note to the segmenter, correctly).
    Silence (f0 NaN) between notes."""
    chunks, f0 = [], []
    frames_per_s = SR / HOP
    gap = np.zeros(int(gap_s * SR))
    for hz, secs, dips in notes:
        n = int(secs * SR)
        amp = np.ones(n)
        cents = np.zeros(n)
        for at_s, dip_amp, pitch_c in dips:
            c = int(at_s * SR)
            w_amp = int(0.05 * SR)
            bump = np.hanning(2 * w_amp)
            amp[c - w_amp:c + w_amp] = 1.0 - (1.0 - dip_amp) * bump
            w_pit = int(0.06 * SR)
            cents[c - w_pit:c + w_pit] = pitch_c * np.hanning(2 * w_pit)
        inst_hz = hz * 2 ** (cents / 1200.0)
        phase = 2 * np.pi * np.cumsum(inst_hz) / SR
        chunks += [gap, amp * np.sin(phase)]
        f0 += [np.full(int(gap_s * frames_per_s), np.nan)]
        f0 += [inst_hz[::HOP][: int(secs * frames_per_s)]]
    chunks.append(gap)
    f0.append(np.full(int(gap_s * frames_per_s), np.nan))
    y = np.concatenate(chunks).astype(np.float32)
    f = np.concatenate(f0)
    n_frames = 1 + len(y) // HOP
    f = np.resize(f, n_frames) if len(f) >= n_frames else np.concatenate([f, np.full(n_frames - len(f), np.nan)])
    return y, f


def test_boundary_excursion_is_read_apart_from_vowel_drift():
    """Six held notes: three clean single-vowel sustains, three with a 'consonant'
    (a 14 dB energy dip) where the pitch is knocked 100 cents. The clean notes
    must report no boundary and near-zero vowel drift; the knocked notes must
    report one boundary with a large excursion — and the take-level read must
    point at the boundaries, not the vowel."""
    y, f0 = _synth([
        (220.0, 1.2, []),
        (247.0, 1.2, [(0.6, 0.2, -100.0)]),
        (262.0, 1.2, []),
        (294.0, 1.2, [(0.6, 0.2, 100.0)]),
        (330.0, 1.2, []),
        (349.0, 1.2, [(0.6, 0.2, 100.0)]),
    ])
    out = A.analyse_word_drift(y, SR, f0, hop_length=HOP)
    assert "error" not in out, out
    assert out["n_notes_analysed"] == 6
    assert out["n_notes_with_boundaries"] == 3
    assert out["pct_notes_with_boundaries"] == 50.0
    clean = [p for p in out["notes"] if p["n_boundaries"] == 0]
    knocked = [p for p in out["notes"] if p["n_boundaries"] == 1]
    assert len(clean) == 3 and len(knocked) == 3
    for p in clean:
        assert p["vowel_drift_cents"] is not None and p["vowel_drift_cents"] < 5.0
        assert p["boundary_excursion_cents"] is None
    for p in knocked:
        assert p["boundary_excursion_cents"] >= 30.0, p       # smoothed 100c knock survives
        assert p["vowel_drift_cents"] < 15.0, p               # and is NOT counted as vowel drift
    assert out["median_vowel_drift_cents"] < 5.0
    assert "knocked off at the word boundaries" in out["read"]
    assert out["worst_boundary_notes"][0]["worst_boundary_excursion_cents"] >= 30.0


def test_a_wandering_vowel_is_not_blamed_on_boundaries():
    """Five clean sustains whose pitch slides 80 cents across the note: no
    boundaries, high vowel drift, and the read must say so."""
    frames_per_s = SR / HOP
    notes = []
    for hz in (220.0, 247.0, 262.0, 294.0, 330.0):
        n = int(1.2 * SR)
        cents = np.linspace(0, 80, n)
        inst = hz * 2 ** (cents / 1200.0)
        notes.append(inst)
    gap = np.zeros(int(0.4 * SR))
    chunks, f0 = [], []
    for inst in notes:
        chunks += [gap, np.sin(2 * np.pi * np.cumsum(inst) / SR)]
        f0 += [np.full(int(0.4 * frames_per_s), np.nan), inst[::HOP][: int(1.2 * frames_per_s)]]
    chunks.append(gap); f0.append(np.full(int(0.4 * frames_per_s), np.nan))
    y = np.concatenate(chunks).astype(np.float32)
    f = np.concatenate(f0)
    n_frames = 1 + len(y) // HOP
    f = np.concatenate([f, np.full(max(0, n_frames - len(f)), np.nan)])[:n_frames]
    out = A.analyse_word_drift(y, SR, f, hop_length=HOP)
    assert "error" not in out, out
    assert out["n_notes_with_boundaries"] == 0
    assert out["median_vowel_drift_cents"] >= 40.0
    assert out["median_boundary_excursion_cents"] is None
    assert "single-word sustains" in out["read"] or "vowels themselves wander" in out["read"]


def test_word_drift_is_a_diagnostic_outside_the_fingerprints():
    """Adding it must move neither the rubric nor the measurement fingerprint —
    Candi's Phase 1 run is verifying against 28e854af22ea."""
    assert A.analyse_word_drift not in A._measurement_functions()
    assert A.measurement_fingerprint() == "28e854af22ea"
    assert "word_drift" not in A.ALL_COMPONENTS
    out = A.analyse_word_drift(np.zeros(SR, dtype=np.float32), SR, np.full(1 + SR // HOP, np.nan))
    assert "error" in out and "n_notes_analysed" in out
