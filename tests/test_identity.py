import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text

from jornada_ms.api.errors import AppError
from jornada_ms.config import Settings
from jornada_ms.main import create_app
from jornada_ms.modules.identity.service import IdentityService, Principal, authorize_roles


@pytest.fixture()
def identity_context(tmp_path: Path):
    repository = Path(__file__).parents[1]
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'identity.db').as_posix()}"
    environment = os.environ.copy()
    environment["JORNADA_MS_DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    settings = Settings(
        database_url=database_url,
        jwt_secret="test-only-jwt-secret-with-more-than-32-chars",
        access_token_expire_seconds=60,
        refresh_token_expire_seconds=3_600,
    )
    app = create_app(settings)
    service = IdentityService(app.state.database, settings)
    service.create_user("Admin@Example.com", "correct horse battery staple", ["ADMIN"])
    try:
        yield app, service
    finally:
        app.state.database.dispose()


@pytest.fixture()
async def identity_client(identity_context):
    app, _service = identity_context
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_login_me_refresh_rotation_and_logout(identity_client: httpx.AsyncClient) -> None:
    login = await identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    first_tokens = login.json()
    assert first_tokens["token_type"] == "Bearer"
    assert "correct horse" not in login.text
    assert "jornada_access=" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=lax" in login.headers["set-cookie"]

    cookie_me = await identity_client.get("/api/v1/me")
    assert cookie_me.status_code == 200
    assert cookie_me.json()["email"] == "admin@example.com"

    me = await identity_client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {first_tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["roles"] == ["ADMIN"]

    rotated = await identity_client.post(
        "/api/v1/auth/refresh",
        json={},
    )
    assert rotated.status_code == 200
    second_tokens = rotated.json()
    assert second_tokens["refresh_token"] != first_tokens["refresh_token"]

    reused = await identity_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_tokens["refresh_token"]},
    )
    assert reused.status_code == 401

    logged_out = await identity_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {second_tokens['access_token']}"},
    )
    assert logged_out.status_code == 204
    assert "Max-Age=0" in logged_out.headers["set-cookie"]

    after_logout = await identity_client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {second_tokens['access_token']}"},
    )
    assert after_logout.status_code == 401


@pytest.mark.anyio
async def test_invalid_credentials_are_safe(identity_client: httpx.AsyncClient) -> None:
    response = await identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong secret"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "wrong secret" not in response.text


@pytest.mark.anyio
async def test_login_rate_limit_returns_retry_after(identity_client: httpx.AsyncClient) -> None:
    for _ in range(5):
        response = await identity_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong secret"},
        )
        assert response.status_code == 401

    blocked = await identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong secret"},
    )

    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]
    assert blocked.json()["error"]["code"] == "TOO_MANY_LOGIN_ATTEMPTS"


def test_email_is_unique_case_insensitively(identity_context) -> None:
    _app, service = identity_context

    with pytest.raises(AppError) as error:
        service.create_user("admin@EXAMPLE.com", "another secure password")

    assert error.value.status_code == 409


def test_rbac_rejects_missing_role() -> None:
    principal = Principal(
        user_id="user-id",
        email="user@example.com",
        roles=("COLLABORATOR",),
        employee_id=None,
        session_id="session-id",
    )

    with pytest.raises(AppError) as error:
        authorize_roles(principal, ["ADMIN"])

    assert error.value.status_code == 403


def test_password_is_stored_as_a_hash(identity_context) -> None:
    app, _service = identity_context
    with create_engine(app.state.settings.database_url).connect() as connection:
        stored = connection.execute(
            text("SELECT password_hash FROM users WHERE email = 'admin@example.com'")
        ).scalar_one()

    assert stored != "correct horse battery staple"
    assert stored.startswith("scrypt$")


def test_production_rejects_the_development_jwt_secret() -> None:
    with pytest.raises(ValueError):
        Settings(environment="production")
