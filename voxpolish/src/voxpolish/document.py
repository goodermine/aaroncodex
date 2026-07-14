"""The Edit Document: every decision the analysis stage makes, as editable data.

This is the contract between analysis and render. Analysis writes it, a human
(or UI) may edit it, render applies it sample-accurately and deterministically.
Nothing in the render stage re-decides anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict


@dataclass
class Region:
    """A time region [start, end) in seconds with a gain decision attached."""

    start: float
    end: float
    reduction_db: float = 0.0
    fade_ms: float = 30.0
    # For band-limited regions (sibilance): [low_hz, high_hz]; None = full band.
    band: list | None = None
    label: str = ""
    # Detector confidence 0..1. Low-confidence edits never override speech
    # guards; 1.0 (the default) keeps hand-authored regions fully trusted.
    confidence: float = 1.0

    def duration(self) -> float:
        return self.end - self.start


@dataclass
class EditDocument:
    sample_rate: int = 44100
    duration: float = 0.0
    mode: str = "voice"  # "song" | "voice"

    # Dynamics: gain automation curve as [time_seconds, gain_db] pairs.
    gain_curve: list = field(default_factory=list)
    # Gate: detected pauses (reduction_db is the gate floor, e.g. -60).
    pauses: list = field(default_factory=list)
    # Breath: detected breath sounds to attenuate.
    breaths: list = field(default_factory=list)
    # Sibilance: harsh consonant events, band-limited reduction.
    sibilants: list = field(default_factory=list)
    # Protected speech intervals [[start, end], ...]: render never lets a full-band
    # attenuation region (pause/breath) touch these, even after hand edits.
    speech_guards: list = field(default_factory=list)
    # Clean: model-based settings (applied before render DSP).
    denoise: dict = field(default_factory=lambda: {"amount": 0.0, "backend": "none"})
    # Analysis context useful to a UI / for debugging, not used by render.
    analysis: dict = field(default_factory=dict)

    def to_json(self) -> str:
        doc = asdict(self)
        return json.dumps(doc, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "EditDocument":
        raw = json.loads(text)
        doc = cls(
            sample_rate=raw.get("sample_rate", 44100),
            duration=raw.get("duration", 0.0),
            mode=raw.get("mode", "voice"),
            gain_curve=raw.get("gain_curve", []),
            speech_guards=raw.get("speech_guards", []),
            denoise=raw.get("denoise", {"amount": 0.0, "backend": "none"}),
            analysis=raw.get("analysis", {}),
        )
        for name in ("pauses", "breaths", "sibilants"):
            setattr(doc, name, [Region(**r) for r in raw.get(name, [])])
        return doc

    def save(self, path) -> None:
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path) -> "EditDocument":
        with open(path) as f:
            return cls.from_json(f.read())
