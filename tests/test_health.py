"""Health and readiness endpoint tests."""

import pytest

from jornada_ms.db.session import DatabaseUnavailable


@pytest.mark.anyio
async def test_live_does_not_require_database(client):
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-correlation-id"]


@pytest.mark.anyio
async def test_live_preserves_safe_correlation_id(client):
    response = await client.get("/health/live", headers={"X-Correlation-ID": "test-123"})

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "test-123"


@pytest.mark.anyio
async def test_ready_checks_database(client):
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.anyio
async def test_ready_returns_safe_error_when_database_is_unavailable(app, client):
    class UnavailableDatabase:
        def check(self):
            raise DatabaseUnavailable("test failure")

    app.state.database = UnavailableDatabase()
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_NOT_READY"
    assert response.json()["error"]["message"] == "Required dependencies are unavailable"
    assert "test failure" not in response.text
