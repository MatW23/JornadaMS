"""Consistent, safe error responses for the HTTP boundary."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette import status


class ErrorBody(BaseModel):
    """Stable error envelope exposed by the API."""

    code: str
    message: str
    details: list[Any] = Field(default_factory=list)
    correlation_id: str


class ErrorResponse(BaseModel):
    """Top-level API error response."""

    error: ErrorBody


class AppError(Exception):
    """Application-facing error that can be rendered without leaking internals."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep validation locations and types without echoing submitted values."""

    return [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "type": str(error.get("type", "validation_error")),
        }
        for error in errors
    ]


def _payload(request: Request, code: str, message: str, details: list[Any] | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "correlation_id": _correlation_id(request),
        }
    }


def register_exception_handlers(app) -> None:
    """Register safe handlers for expected and unexpected HTTP failures."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_409_CONFLICT: "CONFLICT",
            status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
        }.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(request, code, message),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload(
                request,
                "VALIDATION_ERROR",
                "Request validation failed",
                sanitize_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        del exc
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload(request, "INTERNAL_SERVER_ERROR", "Internal server error"),
        )
