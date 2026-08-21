"""HTTP routes and authorization dependencies for identity."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.modules.identity.service import (
    IdentityService,
    Principal,
    authorize_roles,
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=512)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserContext(BaseModel):
    user_id: str
    email: str
    roles: list[str]
    employee_id: str | None = None


router = APIRouter(prefix="/api/v1", tags=["Auth"])
_bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


def get_identity_service(request: Request) -> IdentityService:
    return IdentityService(request.app.state.database, request.app.state.settings)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def _extract_bearer(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("UNAUTHORIZED", "Authentication is required", status_code=401)
    token = credentials.credentials.strip()
    if not token:
        raise AppError("UNAUTHORIZED", "Authentication is required", status_code=401)
    return token


async def get_current_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ] = None,
    service: IdentityService = Depends(get_identity_service),
) -> Principal:
    return service.current_principal(_extract_bearer(credentials))


def require_roles(*roles: str):
    """Build a FastAPI dependency enforcing one of the required roles."""

    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        return authorize_roles(principal, roles)

    return dependency


@router.post(
    "/auth/login",
    operation_id="login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def login(
    payload: LoginRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service),
) -> LoginResponse:
    tokens = service.login(
        payload.email,
        payload.password,
        _correlation_id(request),
        _client_ip(request),
    )
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/auth/refresh",
    operation_id="refreshSession",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse}},
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service),
) -> LoginResponse:
    tokens = service.refresh(
        payload.refresh_token,
        _correlation_id(request),
        _client_ip(request),
    )
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/auth/logout",
    operation_id="logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}},
)
async def logout(
    request: Request,
    principal: Principal = Depends(get_current_principal),
    service: IdentityService = Depends(get_identity_service),
) -> Response:
    service.logout(principal, _correlation_id(request), _client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    operation_id="getCurrentUser",
    response_model=UserContext,
    responses={401: {"model": ErrorResponse}},
)
async def current_user(principal: Principal = Depends(get_current_principal)) -> UserContext:
    return UserContext(
        user_id=principal.user_id,
        email=principal.email,
        roles=list(principal.roles),
        employee_id=principal.employee_id,
    )
