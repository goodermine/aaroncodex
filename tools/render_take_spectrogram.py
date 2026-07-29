#!/usr/bin/env python3
"""Render a whole take as one spectrogram with the sung pitch drawn over it.

This is the after-the-take, full-song counterpart to the live SPEC view in the
pitch monitor (`pitchmonitor/index.html`). The live view scrolls ~3 seconds at a
time; this draws the entire take in one image so a phrase, a whole song, or a
practice loop can be read at a glance — the same look on purpose: an inferno
spectrogram on a log-frequency axis with note lines, the 2–4 kHz singer's "ring"
band marked, and the pitch contour laid over the top in bright green.

Honesty about the pitch line matches the monitor: it is drawn SOLID where the
detector was confident the frame was voiced, and DOTTED where it was not — a
guessed pitch never looks as certain as a real one. Confidence here is pyin's
voiced-probability (a research-standard tracker that reports its own certainty),
so a static full-take render can show it without the live YIN's per-frame state.

This is a VISUALISATION, not a score. It computes no `/10` and touches none of
the scoring path — rule 1 of CLAUDE.md is about scores, and this draws a picture.

    python3 tools/render_take_spectrogram.py IN_AUDIO OUT_PNG [--title "..."]

Any format ffmpeg/librosa can read. Writes a wide PNG (default 2000×620).
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np


# The monitor's fixed spectrogram axis and colours, mirrored so the two views
# read identically.
F_LO, F_HI = 55.0, 8000.0          # log-frequency axis bounds (Hz)
RING_LO, RING_HI = 2000.0, 4000.0  # singer's-formant "ring" band
PITCH_GREEN = "#39ff14"            # the bright-green pitch line, as in SPEC view
FMIN, FMAX = 65.0, 1000.0          # default pyin search range (override per take)
STABLE_CENTS = 70.0                # within this of the local median = a steady note = solid


def _c_note_lines():
    """C2..C8 in Hz, for the horizontal note guides / axis labels."""
    # MIDI 36=C2 … 108=C8, A4=440 at MIDI 69.
    out = []
    for midi in range(36, 109, 12):
        f = 440.0 * 2 ** ((midi - 69) / 12.0)
        if F_LO <= f <= F_HI:
            out.append((f, "C%d" % (midi // 12 - 1)))
    return out


def render(in_path: str, out_path: str, title: str | None = None,
           width: float = 20.0, height: float = 6.2,
           fmin: float = FMIN, fmax: float = FMAX) -> None:
    import librosa
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    y, sr = librosa.load(in_path, sr=22050, mono=True)
    if y.size == 0:
        raise SystemExit("empty audio")

    n_fft, hop = 2048, 512
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    Sdb = librosa.amplitude_to_db(S, ref=np.max)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    times = librosa.times_like(Sdb, sr=sr, hop_length=hop)

    # keep only bins inside the drawn band (avoid a log(0) row and dead space)
    band = (freqs >= F_LO) & (freqs <= F_HI)
    freqs_b, Sdb_b = freqs[band], Sdb[band]

    # pitch track. pyin's voiced_probs is unreliable on reverberant live stems
    # (near-zero even on clear notes), so confidence comes from pitch STABILITY
    # below, not from vprob.
    f0, voiced, _ = librosa.pyin(
        y, sr=sr, fmin=fmin, fmax=fmax, frame_length=n_fft, hop_length=hop)
    ptimes = librosa.times_like(f0, sr=sr, hop_length=hop)

    fig, ax = plt.subplots(figsize=(width, height), dpi=100)
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")

    ax.pcolormesh(times, freqs_b, Sdb_b, cmap="inferno", vmin=-80, vmax=0,
                  shading="auto")
    ax.set_yscale("log")
    ax.set_ylim(F_LO, F_HI)
    ax.set_xlim(times[0], times[-1])

    # ring band
    ax.axhspan(RING_LO, RING_HI, color="#3fe0ff", alpha=0.08, zorder=2)
    for fb in (RING_LO, RING_HI):
        ax.axhline(fb, color="#3fe0ff", alpha=0.35, lw=0.8, zorder=2)
    ax.text(times[0] + (times[-1] - times[0]) * 0.004, RING_HI * 0.97,
            "RING 2–4k", color="#3fe0ff", fontsize=9, va="top",
            family="monospace", zorder=6)

    # note lines + labels
    ticks, labels = [], []
    for f, name in _c_note_lines():
        ax.axhline(f, color="#8090a0", alpha=0.16, lw=0.8, zorder=2)
        ticks.append(f); labels.append(name)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, color="#c7ced4", fontsize=9, family="monospace")
    ax.tick_params(axis="x", colors="#9aa3ad")
    ax.tick_params(axis="y", length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    # confidence = pitch stability. A frame is confident (solid) when its pitch
    # sits within STABLE_CENTS of the local median — a steady, held note. Lone
    # frames and octave jumps land far from the median and draw dotted, so a
    # glitchy or guessed pitch is never shown as certain.
    valid = ~np.isnan(f0)
    cents = 1200.0 * np.log2(np.where(valid, f0, np.nan) / fmin)
    loc = np.full_like(cents, np.nan)
    for i in range(cents.size):
        w = cents[max(0, i - 3):i + 4]
        w = w[~np.isnan(w)]
        if w.size:
            loc[i] = np.median(w)
    conf_mask = valid & (np.abs(cents - loc) < STABLE_CENTS)
    unsure_mask = valid & ~conf_mask

    def _plot(mask, **kw):
        f = np.where(mask, f0, np.nan)
        ax.plot(ptimes, f, color=PITCH_GREEN, solid_capstyle="round", **kw)

    _plot(unsure_mask, lw=1.6, ls=(0, (1, 2)), alpha=0.9, zorder=4)
    _plot(conf_mask, lw=2.4, zorder=5)

    ax.set_xlabel("time (s)", color="#9aa3ad", fontsize=9)
    if title:
        ax.set_title(title, color="#f4f6f8", fontsize=13, pad=8)

    fig.tight_layout()
    fig.savefig(out_path, facecolor="#000000", dpi=100)
    plt.close(fig)

    voiced_pct = float(np.mean(conf_mask)) * 100.0
    print("wrote %s  (%.0fs, %.0f%% frames confidently voiced)"
          % (out_path, times[-1], voiced_pct))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_audio")
    ap.add_argument("out_png")
    ap.add_argument("--title", default=None)
    ap.add_argument("--width", type=float, default=20.0)
    ap.add_argument("--height", type=float, default=6.2)
    ap.add_argument("--fmin", type=float, default=FMIN,
                    help="pitch floor Hz; raise it (e.g. 140) on a rumbly/reverberant "
                         "take so the tracker doesn't latch onto low-frequency bleed")
    ap.add_argument("--fmax", type=float, default=FMAX, help="pitch ceiling Hz")
    a = ap.parse_args()
    if not os.path.isfile(a.in_audio):
        print("no such file: %s" % a.in_audio, file=sys.stderr)
        return 1
    render(a.in_audio, a.out_png, a.title, a.width, a.height, a.fmin, a.fmax)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
