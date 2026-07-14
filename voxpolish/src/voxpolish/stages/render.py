"""Render stage: apply an Edit Document to audio, sample-accurately.

Pure deterministic DSP — no ML, no decisions. The same (audio, document) input
always produces bit-identical output; that's what makes manual edits to the
document trustworthy.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .. import dsp
from ..document import EditDocument


def subtract_guards(regions: list, guards: list) -> list:
    """Trim (splitting where needed) attenuation regions so none overlaps a
    protected speech guard. This is the render-time safety invariant: it holds
    even for hand-edited documents whose regions were moved onto speech."""
    if not guards:
        return list(regions)
    out = []
    for r in regions:
        pieces = [[r.start, r.end]]
        for gs, ge in guards:
            trimmed = []
            for s, e in pieces:
                if ge <= s or gs >= e:
                    trimmed.append([s, e])
                    continue
                if gs > s:
                    trimmed.append([s, gs])
                if ge < e:
                    trimmed.append([ge, e])
            pieces = trimmed
        for s, e in pieces:
            if e - s > 1e-3:
                out.append(replace(r, start=s, end=e))
    return out


def render(audio: np.ndarray, sr: int, doc: EditDocument) -> np.ndarray:
    audio = np.atleast_2d(audio)
    n = audio.shape[1]

    # Render-time controls: bypass skips a module's layer without touching its
    # data; amounts scale the layer (1.0 = as analyzed).
    bypass = doc.bypass or {}
    amounts = {"dynamics": 1.0, "breath": 1.0, "sibilance": 1.0, **(doc.amounts or {})}

    # 1. Full-band gain envelope: dynamics curve + gate pauses + breath dips.
    # Pauses and breaths are hard-trimmed against the speech guards first.
    env_db = np.zeros(n, dtype=np.float64)
    if doc.gain_curve and not bypass.get("dynamics"):
        curve = np.asarray(doc.gain_curve, dtype=np.float64)
        t = np.arange(n) / sr
        env_db += np.interp(t, curve[:, 0], curve[:, 1]) * amounts["dynamics"]
    if not bypass.get("gate"):
        env_db += dsp.fade_envelope(n, sr, subtract_guards(doc.pauses, doc.speech_guards))
    if not bypass.get("breath"):
        breaths = [
            replace(b, reduction_db=b.reduction_db * amounts["breath"])
            for b in doc.breaths
        ]
        env_db += dsp.fade_envelope(n, sr, subtract_guards(breaths, doc.speech_guards))
    gain = 10 ** (env_db / 20)

    out = audio.astype(np.float64) * gain[None, :]

    # 2. Sibilance: band-limited reduction inside each event region.
    sibilants = [] if bypass.get("sibilance") else doc.sibilants
    for region in sibilants:
        s = max(0, int(round(region.start * sr)))
        e = min(n, int(round(region.end * sr)))
        if e <= s or not region.band:
            continue
        pad = int(0.05 * sr)  # filter context so filtfilt edges stay clean
        ps, pe = max(0, s - pad), min(n, e + pad)
        fade = min(int(region.fade_ms / 1000 * sr), (e - s) // 2)
        red = 10 ** (region.reduction_db * amounts["sibilance"] / 20)
        for ch in range(out.shape[0]):
            seg = out[ch, ps:pe]
            low, high = dsp.band_split(seg, sr, region.band[0])
            g = np.ones(len(seg))
            i0, i1 = s - ps, e - ps
            g[i0:i1] = red
            if fade > 0:
                g[i0 : i0 + fade] = np.linspace(1.0, red, fade)
                g[i1 - fade : i1] = np.linspace(red, 1.0, fade)
            out[ch, ps:pe] = low + high * g

    return np.clip(out, -1.0, 1.0).astype(np.float32)
