"""Operational health endpoints kept outside the versioned API."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import DatabaseUnavailable

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    """Confirm that the process is accepting requests."""

    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={
        503: {
            "description": "Database unavailable",
            "model": ErrorResponse,
        }
    },
)
async def ready(request: Request) -> HealthResponse:
    """Confirm that required runtime dependencies are reachable."""

    try:
        request.app.state.database.check()
    except DatabaseUnavailable as exc:
        raise AppError(
            "SERVICE_NOT_READY",
            "Required dependencies are unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    return HealthResponse(status="ready")
