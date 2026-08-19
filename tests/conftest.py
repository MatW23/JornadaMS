"""Shared test fixtures for the foundation layer."""

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from jornada_ms.config import Settings
from jornada_ms.db.session import Database
from jornada_ms.main import create_app


@pytest.fixture()
def app():
    settings = Settings(database_url="sqlite+pysqlite:///:memory:")
    application = create_app(settings)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    application.state.database = Database(engine=engine)
    return application


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
