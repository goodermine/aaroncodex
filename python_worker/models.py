from __future__ import annotations

import platform
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str
    pythonVersion: str

    @classmethod
    def build(cls) -> "HealthResponse":
        return cls(
            ok=True,
            service="vox-python-worker",
            version="0.1.0",
            pythonVersion=platform.python_version(),
        )


class SeparationRequest(BaseModel):
    jobId: str
    inputPath: str
    outputDir: str
    stemMode: str = "vocals_instrumental"
    cleanupIntermediate: bool = False
    modelFilename: Optional[str] = None


class StemArtifact(BaseModel):
    path: str
    format: str = "wav"
    sampleRate: Optional[int] = None
    channels: Optional[int] = None
    durationSec: Optional[float] = None


class EngineMetadata(BaseModel):
    name: str
    version: str
    model: Optional[str] = None


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: Optional[str] = None


class SeparationResponse(BaseModel):
    ok: bool
    jobId: str
    engine: Optional[EngineMetadata] = None
    outputs: Dict[str, StemArtifact] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorPayload] = None
