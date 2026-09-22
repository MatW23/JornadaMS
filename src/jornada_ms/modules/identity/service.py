"""Identity use cases and persistence boundary."""

import hashlib
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

from jornada_ms.api.errors import AppError
from jornada_ms.config import Settings
from jornada_ms.db.session import Database
from jornada_ms.modules.audit.service import record_audit
from jornada_ms.modules.identity.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DUMMY_PASSWORD_HASH = hash_password("jornada-ms-dummy-password")


@dataclass(frozen=True, slots=True)
class Principal:
    """Authenticated user context used by protected routes and RBAC."""

    user_id: str
    email: str
    roles: tuple[str, ...]
    employee_id: str | None
    session_id: str


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Access token plus its opaque, rotatable refresh token."""

    access_token: str
    refresh_token: str
    expires_in: int


def normalize_email(email: str) -> str:
    """Normalize email addresses before lookup and persistence."""

    normalized = email.strip().casefold()
    if not normalized or len(normalized) > 320 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise AppError(
            "INVALID_EMAIL",
            "Email is invalid",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def normalize_role(role: str) -> str:
    normalized = role.strip().upper()
    if not normalized or len(normalized) > 64:
        raise AppError(
            "INVALID_ROLE",
            "Role is invalid",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def authorize_roles(principal: Principal, allowed_roles: Iterable[str]) -> Principal:
    """Authorize a principal when at least one required role is present."""

    required = {normalize_role(role) for role in allowed_roles}
    if not required.intersection(principal.roles):
        raise AppError(
            "FORBIDDEN",
            "User does not have the required role",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return principal


class IdentityService:
    """Application service for credentials, sessions and role checks."""

    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def create_user(self, email: str, password: str, roles: Iterable[str] = ()) -> str:
        """Create a user and its initial role assignments for provisioning/tests."""

        normalized_email = normalize_email(email)
        if len(password) < 8:
            raise AppError(
                "INVALID_PASSWORD",
                "Password must contain at least 8 characters",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        user_id = str(uuid4())
        password_hash = hash_password(password)
        try:
            with self.database.engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO users (id, email, password_hash) "
                        "VALUES (:id, :email, :password_hash)"
                    ),
                    {"id": user_id, "email": normalized_email, "password_hash": password_hash},
                )
                for role in roles:
                    role_id = self._ensure_role(connection, role)
                    connection.execute(
                        text(
                            "INSERT INTO user_roles (user_id, role_id) "
                            "VALUES (:user_id, :role_id)"
                        ),
                        {"user_id": user_id, "role_id": role_id},
                    )
        except IntegrityError as exc:
            raise AppError(
                "USER_ALREADY_EXISTS",
                "A user with this email already exists",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc
        except SQLAlchemyError as exc:
            raise self._service_unavailable(exc) from exc
        return user_id

    def login(
        self, email: str, password: str, correlation_id: str, ip_address: str | None
    ) -> TokenPair:
        """Authenticate credentials and create a refresh session."""

        normalized_email = normalize_email(email)
        result: TokenPair | None = None
        failed = False
        try:
            with self.database.engine.begin() as connection:
                user = connection.execute(
                    text(
                        "SELECT id, email, password_hash, status "
                        "FROM users WHERE lower(email) = :email"
                    ),
                    {"email": normalized_email},
                ).mappings().first()
                stored_hash = user["password_hash"] if user else _DUMMY_PASSWORD_HASH
                valid = verify_password(password, stored_hash)
                if not valid or user["status"] != "ACTIVE":
                    self._record_audit(
                        connection,
                        actor_id=str(user["id"]) if user else None,
                        entity_id=str(user["id"]) if user else None,
                        action="AUTH_LOGIN",
                        result="FAILURE",
                        correlation_id=correlation_id,
                        ip_address=ip_address,
                    )
                    failed = True
                else:
                    roles = self._load_roles(connection, str(user["id"]))
                    session_id, refresh_token = self._create_session(
                        connection,
                        user_id=str(user["id"]),
                        ip_address=ip_address,
                    )
                    now = _utc_now()
                    connection.execute(
                        text("UPDATE users SET last_login_at = :now WHERE id = :user_id"),
                        {"now": now, "user_id": str(user["id"])},
                    )
                    self._record_audit(
                        connection,
                        actor_id=str(user["id"]),
                        entity_id=str(user["id"]),
                        action="AUTH_LOGIN",
                        result="SUCCESS",
                        correlation_id=correlation_id,
                        ip_address=ip_address,
                    )
                    result = self._token_pair(str(user["id"]), session_id, roles, refresh_token)
        except SQLAlchemyError as exc:
            raise self._service_unavailable(exc) from exc
        if failed or result is None:
            raise AppError("INVALID_CREDENTIALS", "Invalid email or password", status_code=401)
        return result

    def refresh(self, refresh_token: str, correlation_id: str, ip_address: str | None) -> TokenPair:
        """Rotate a refresh token and revoke the token that was presented."""

        token_hash = _hash_refresh_token(refresh_token)
        result: TokenPair | None = None
        try:
            with self.database.engine.begin() as connection:
                query = (
                    "SELECT s.id AS session_id, s.user_id, s.expires_at, s.revoked_at, "
                    "u.status FROM sessions s JOIN users u ON u.id = s.user_id "
                    "WHERE s.token_hash = :token_hash"
                )
                if connection.dialect.name == "postgresql":
                    query += " FOR UPDATE"
                session = (
                    connection.execute(text(query), {"token_hash": token_hash})
                    .mappings()
                    .first()
                )
                if (
                    not session
                    or session["revoked_at"] is not None
                    or _is_expired(session["expires_at"])
                    or session["status"] != "ACTIVE"
                ):
                    raise AppError(
                        "INVALID_REFRESH_TOKEN",
                        "Refresh token is invalid",
                        status_code=401,
                    )

                user_id = str(session["user_id"])
                roles = self._load_roles(connection, user_id)
                now = _utc_now()
                connection.execute(
                    text(
                        "UPDATE sessions SET revoked_at = :now, last_used_at = :now "
                        "WHERE id = :session_id"
                    ),
                    {"now": now, "session_id": str(session["session_id"])},
                )
                new_session_id, new_refresh_token = self._create_session(
                    connection,
                    user_id=user_id,
                    ip_address=ip_address,
                )
                self._record_audit(
                    connection,
                    actor_id=user_id,
                    entity_id=user_id,
                    action="AUTH_REFRESH",
                    result="SUCCESS",
                    correlation_id=correlation_id,
                    ip_address=ip_address,
                )
                result = self._token_pair(user_id, new_session_id, roles, new_refresh_token)
        except AppError:
            raise
        except SQLAlchemyError as exc:
            raise self._service_unavailable(exc) from exc
        if result is None:
            raise AppError("INVALID_REFRESH_TOKEN", "Refresh token is invalid", status_code=401)
        return result

    def current_principal(self, access_token: str) -> Principal:
        """Validate a JWT and its backing session before authorizing a request."""

        try:
            claims = decode_access_token(
                access_token,
                secret=self.settings.jwt_secret,
                issuer=self.settings.jwt_issuer,
                audience=self.settings.jwt_audience,
            )
        except TokenError as exc:
            raise AppError("UNAUTHORIZED", "Authentication is required", status_code=401) from exc

        try:
            with self.database.engine.connect() as connection:
                session = connection.execute(
                    text(
                        "SELECT s.user_id, s.expires_at, s.revoked_at, u.email, u.status "
                        "FROM sessions s JOIN users u ON u.id = s.user_id "
                        "WHERE s.id = :session_id AND s.user_id = :user_id"
                    ),
                    {"session_id": claims["sid"], "user_id": claims["sub"]},
                ).mappings().first()
                if (
                    not session
                    or session["revoked_at"] is not None
                    or _is_expired(session["expires_at"])
                    or session["status"] != "ACTIVE"
                ):
                    raise AppError("UNAUTHORIZED", "Authentication is required", status_code=401)
                roles = self._load_roles(connection, str(session["user_id"]))
                employee = connection.execute(
                    text("SELECT id FROM employees WHERE user_id = :user_id"),
                    {"user_id": str(session["user_id"])},
                ).scalar_one_or_none()
                return Principal(
                    user_id=str(session["user_id"]),
                    email=str(session["email"]),
                    roles=roles,
                    employee_id=str(employee) if employee is not None else None,
                    session_id=str(claims["sid"]),
                )
        except AppError:
            raise
        except SQLAlchemyError as exc:
            raise self._service_unavailable(exc) from exc

    def logout(self, principal: Principal, correlation_id: str, ip_address: str | None) -> None:
        """Revoke the current session and audit the logout."""

        try:
            with self.database.engine.begin() as connection:
                now = _utc_now()
                connection.execute(
                    text(
                        "UPDATE sessions SET revoked_at = COALESCE(revoked_at, :now), "
                        "last_used_at = :now WHERE id = :session_id AND user_id = :user_id"
                    ),
                    {"now": now, "session_id": principal.session_id, "user_id": principal.user_id},
                )
                self._record_audit(
                    connection,
                    actor_id=principal.user_id,
                    entity_id=principal.user_id,
                    action="AUTH_LOGOUT",
                    result="SUCCESS",
                    correlation_id=correlation_id,
                    ip_address=ip_address,
                )
        except SQLAlchemyError as exc:
            raise self._service_unavailable(exc) from exc

    def _ensure_role(self, connection: Any, role: str) -> str:
        normalized_role = normalize_role(role)
        existing = connection.execute(
            text("SELECT id FROM roles WHERE name = :name"), {"name": normalized_role}
        ).scalar_one_or_none()
        if existing is not None:
            return str(existing)
        role_id = str(uuid4())
        connection.execute(
            text("INSERT INTO roles (id, name) VALUES (:id, :name)"),
            {"id": role_id, "name": normalized_role},
        )
        return role_id

    def _load_roles(self, connection: Any, user_id: str) -> tuple[str, ...]:
        rows = connection.execute(
            text(
                "SELECT r.name FROM roles r "
                "JOIN user_roles ur ON ur.role_id = r.id "
                "WHERE ur.user_id = :user_id ORDER BY r.name"
            ),
            {"user_id": user_id},
        ).scalars()
        return tuple(str(role) for role in rows)

    def _create_session(
        self,
        connection: Any,
        *,
        user_id: str,
        ip_address: str | None,
    ) -> tuple[str, str]:
        session_id = str(uuid4())
        refresh_token = secrets.token_urlsafe(48)
        now = _utc_now()
        connection.execute(
            text(
                "INSERT INTO sessions "
                "(id, user_id, token_hash, expires_at, ip_address) "
                "VALUES (:id, :user_id, :token_hash, :expires_at, :ip_address)"
            ),
            {
                "id": session_id,
                "user_id": user_id,
                "token_hash": _hash_refresh_token(refresh_token),
                "expires_at": now + timedelta(seconds=self.settings.refresh_token_expire_seconds),
                "ip_address": ip_address,
            },
        )
        return session_id, refresh_token

    def _token_pair(
        self,
        user_id: str,
        session_id: str,
        roles: tuple[str, ...],
        refresh_token: str,
    ) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(
                subject=user_id,
                session_id=session_id,
                roles=list(roles),
                secret=self.settings.jwt_secret,
                issuer=self.settings.jwt_issuer,
                audience=self.settings.jwt_audience,
                expires_in=self.settings.access_token_expire_seconds,
            ),
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_expire_seconds,
        )

    @staticmethod
    def _record_audit(
        connection: Any,
        *,
        actor_id: str | None,
        entity_id: str | None,
        action: str,
        result: str,
        correlation_id: str,
        ip_address: str | None,
    ) -> None:
        record_audit(
            connection,
            actor_id=actor_id,
            action=action,
            entity_type="USER",
            entity_id=entity_id,
            result=result,
            correlation_id=correlation_id,
            ip_address=ip_address,
        )

    @staticmethod
    def _service_unavailable(exc: SQLAlchemyError) -> AppError:
        return AppError(
            "SERVICE_UNAVAILABLE",
            "Identity service is temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=[],
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _is_expired(value: datetime | str) -> bool:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= _utc_now()


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
