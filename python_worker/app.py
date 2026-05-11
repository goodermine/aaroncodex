from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .models import HealthResponse, SeparationRequest, SeparationResponse
from .services.separate import run_separation

app = FastAPI(title="VOX Python Worker", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
@app.post("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse.build()


@app.post("/separate", response_model=SeparationResponse)
def separate(request: SeparationRequest) -> SeparationResponse:
    try:
        return run_separation(request)
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "jobId": request.jobId,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": str(exc),
                },
                "warnings": [],
            },
        )
    except Exception as exc:  # pragma: no cover - runtime protection
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "jobId": request.jobId,
                "error": {
                    "code": "SEPARATION_FAILED",
                    "message": str(exc),
                },
                "warnings": [],
            },
        )
