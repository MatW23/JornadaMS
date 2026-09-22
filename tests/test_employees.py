"""Integration coverage for the first employee workflow."""

import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from jornada_ms.config import Settings
from jornada_ms.main import create_app
from jornada_ms.modules.identity.service import IdentityService


@pytest.fixture()
def employee_context(tmp_path: Path):
    repository = Path(__file__).parents[1]
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'employees.db').as_posix()}"
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
        database_url=database_url, jwt_secret="test-only-jwt-secret-with-more-than-32-chars"
    )
    app = create_app(settings)
    IdentityService(app.state.database, settings).create_user(
        "admin@example.com", "correct horse battery staple", ["ADMIN"]
    )
    try:
        yield app
    finally:
        app.state.database.dispose()


@pytest.fixture()
async def employee_client(employee_context):
    transport = httpx.ASGITransport(app=employee_context)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_admin_can_create_and_update_employee(employee_client: httpx.AsyncClient) -> None:
    login = await employee_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    company = await employee_client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Empresa Demo",
            "cnpj": "12345678000199",
            "default_timezone": "America/Sao_Paulo",
        },
    )
    assert company.status_code == 201

    branch = await employee_client.post(
        "/api/v1/branches",
        headers=headers,
        json={
            "company_id": company.json()["id"],
            "name": "Matriz",
            "code": "MATRIZ",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert branch.status_code == 201

    employee = await employee_client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "Maria da Silva",
            "registration_code": "001",
            "branch_id": branch.json()["id"],
        },
    )
    assert employee.status_code == 201
    assert employee.json()["company_id"] == company.json()["id"]

    listing = await employee_client.get("/api/v1/employees?search=maria", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total_items"] == 1

    updated = await employee_client.patch(
        f"/api/v1/employees/{employee.json()['id']}",
        headers=headers,
        json={"name": "Maria da Silva Santos"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Maria da Silva Santos"

    deactivated = await employee_client.post(
        f"/api/v1/employees/{employee.json()['id']}/deactivate",
        headers=headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "INACTIVE"

    activated = await employee_client.post(
        f"/api/v1/employees/{employee.json()['id']}/activate",
        headers=headers,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"


@pytest.mark.anyio
async def test_attendance_enforces_entry_exit_sequence(employee_client: httpx.AsyncClient) -> None:
    login = await employee_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    company = await employee_client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Empresa Ponto",
            "cnpj": "98765432000188",
            "default_timezone": "America/Sao_Paulo",
        },
    )
    branch = await employee_client.post(
        "/api/v1/branches",
        headers=headers,
        json={
            "company_id": company.json()["id"],
            "name": "Matriz",
            "code": "PONTO",
            "timezone": "America/Sao_Paulo",
        },
    )
    employee = await employee_client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "João do Ponto",
            "registration_code": "002",
            "branch_id": branch.json()["id"],
        },
    )
    employee_id = employee.json()["id"]
    schedule = await employee_client.post(
        "/api/v1/work-schedules",
        headers=headers,
        json={"name": "Ponto", "start_time": "08:00:00", "end_time": "17:00:00"},
    )
    await employee_client.post(
        f"/api/v1/employees/{employee_id}/schedules",
        headers=headers,
        json={"schedule_id": schedule.json()["id"], "starts_on": "2026-09-21"},
    )
    event_headers = {**headers, "Idempotency-Key": "attendance-entry-1"}

    entry = await employee_client.post(
        "/api/v1/time-events",
        headers=event_headers,
        json={
            "employee_id": employee_id,
            "event_type": "ENTRADA",
            "occurred_at": "2026-09-21T08:00:00-03:00",
            "source": "WEB",
        },
    )
    assert entry.status_code == 201
    assert entry.json()["daily_summary"]["status"] == "IN_PROGRESS"
    retry = await employee_client.post(
        "/api/v1/time-events",
        headers=event_headers,
        json={
            "employee_id": employee_id,
            "event_type": "ENTRADA",
            "occurred_at": "2026-09-21T08:00:00-03:00",
            "source": "WEB",
        },
    )
    assert retry.status_code == 200

    reused_key = await employee_client.post(
        "/api/v1/time-events",
        headers=event_headers,
        json={
            "employee_id": employee_id,
            "event_type": "ENTRADA",
            "occurred_at": "2026-09-21T08:01:00-03:00",
            "source": "WEB",
        },
    )
    assert reused_key.status_code == 409
    assert reused_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    repeated_entry = await employee_client.post(
        "/api/v1/time-events",
        headers={**headers, "Idempotency-Key": "attendance-entry-2"},
        json={
            "employee_id": employee_id,
            "event_type": "ENTRADA",
            "occurred_at": "2026-09-21T08:05:00-03:00",
            "source": "WEB",
        },
    )
    assert repeated_entry.status_code == 409

    exit_event = await employee_client.post(
        "/api/v1/time-events",
        headers={**headers, "Idempotency-Key": "attendance-exit-1"},
        json={
            "employee_id": employee_id,
            "event_type": "SAIDA",
            "occurred_at": "2026-09-21T17:00:00-03:00",
            "source": "WEB",
        },
    )
    assert exit_event.status_code == 201
    assert exit_event.json()["daily_summary"]["scheduled_minutes"] == 540
    assert exit_event.json()["daily_summary"]["worked_minutes"] == 540
    assert exit_event.json()["daily_summary"]["balance_minutes"] == 0

    history = await employee_client.get(
        "/api/v1/time-events?from=2026-09-21&to=2026-09-21&employee_id=" + employee_id,
        headers=headers,
    )
    assert history.status_code == 200
    assert history.json()["total_items"] == 2

    missing_key = await employee_client.post(
        "/api/v1/time-events",
        headers=headers,
        json={
            "employee_id": employee_id,
            "event_type": "ENTRADA",
            "occurred_at": "2026-09-22T08:00:00-03:00",
            "source": "WEB",
        },
    )
    assert missing_key.status_code == 422


@pytest.mark.anyio
async def test_admin_can_create_and_assign_work_schedule(
    employee_client: httpx.AsyncClient,
) -> None:
    login = await employee_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    company = await employee_client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Empresa Jornada",
            "cnpj": "11222333000144",
            "default_timezone": "America/Sao_Paulo",
        },
    )
    branch = await employee_client.post(
        "/api/v1/branches",
        headers=headers,
        json={
            "company_id": company.json()["id"],
            "name": "Matriz",
            "code": "JORNADA",
            "timezone": "America/Sao_Paulo",
        },
    )
    employee = await employee_client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "name": "Ana da Jornada",
            "registration_code": "003",
            "branch_id": branch.json()["id"],
        },
    )
    schedule = await employee_client.post(
        "/api/v1/work-schedules",
        headers=headers,
        json={
            "name": "Comercial",
            "start_time": "08:00:00",
            "end_time": "17:00:00",
            "tolerance_minutes": 10,
        },
    )
    assert schedule.status_code == 201
    assert schedule.json()["start_time"] == "08:00:00"

    assignment = await employee_client.post(
        f"/api/v1/employees/{employee.json()['id']}/schedules",
        headers=headers,
        json={"schedule_id": schedule.json()["id"], "starts_on": "2026-09-21"},
    )
    assert assignment.status_code == 201
    assert assignment.json()["employee_id"] == employee.json()["id"]

    overlap = await employee_client.post(
        f"/api/v1/employees/{employee.json()['id']}/schedules",
        headers=headers,
        json={"schedule_id": schedule.json()["id"], "starts_on": "2026-09-22"},
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "SCHEDULE_OVERLAP"

    updated = await employee_client.patch(
        f"/api/v1/work-schedules/{schedule.json()['id']}",
        headers=headers,
        json={"start_time": "09:00:00", "end_time": "18:00:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["start_time"] == "09:00:00"
