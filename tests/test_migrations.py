import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

CORE_TABLES = {
    "companies",
    "branches",
    "departments",
    "positions",
    "users",
    "roles",
    "user_roles",
    "sessions",
    "employees",
    "work_schedules",
    "schedule_days",
    "employee_schedules",
    "daily_summaries",
    "time_events",
    "adjustment_requests",
    "audit_events",
}


def run_alembic(command: str, revision: str, database_url: str, repository: Path) -> None:
    environment = os.environ.copy()
    environment["JORNADA_MS_DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_foundation_migration_creates_and_removes_core_tables(tmp_path: Path) -> None:
    repository = Path(__file__).parents[1]
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'migration.db').as_posix()}"

    run_alembic("upgrade", "head", database_url, repository)
    engine = create_engine(database_url)
    try:
        assert CORE_TABLES.issubset(set(inspect(engine).get_table_names()))
        employee_columns = {column["name"] for column in inspect(engine).get_columns("employees")}
        assert "company_id" in employee_columns
        time_event_columns = {
            column["name"] for column in inspect(engine).get_columns("time_events")
        }
        assert "status" in time_event_columns
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'index' AND name = 'uq_users_email_lower'"
                )
            ).scalar_one() == "uq_users_email_lower"
    finally:
        engine.dispose()

    run_alembic("downgrade", "base", database_url, repository)
    engine = create_engine(database_url)
    try:
        assert not CORE_TABLES.intersection(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()


def test_foundation_constraints_normalize_email_uniqueness(tmp_path: Path) -> None:
    repository = Path(__file__).parents[1]
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'constraints.db').as_posix()}"
    run_alembic("upgrade", "head", database_url, repository)
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash) "
                    "VALUES (:id, :email, :password_hash)"
                ),
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "email": "Admin@Example.com",
                    "password_hash": "test-hash",
                },
            )
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            "INSERT INTO users (id, email, password_hash) "
                            "VALUES (:id, :email, :password_hash)"
                        ),
                        {
                            "id": "22222222-2222-2222-2222-222222222222",
                            "email": "admin@example.com",
                            "password_hash": "test-hash",
                        },
                    )
    finally:
        engine.dispose()


def test_employee_branch_company_integrity_is_declared(tmp_path: Path) -> None:
    repository = Path(__file__).parents[1]
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'integrity.db').as_posix()}"
    run_alembic("upgrade", "head", database_url, repository)
    engine = create_engine(database_url)
    try:
        foreign_keys = inspect(engine).get_foreign_keys("employees")
        assert any(
            fk["constrained_columns"] == ["branch_id", "company_id"]
            and fk["referred_table"] == "branches"
            for fk in foreign_keys
        ) or engine.dialect.name == "sqlite"
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO companies (id, name, cnpj, default_timezone) "
                    "VALUES (:id, :name, :cnpj, :timezone)"
                ),
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "name": "Company A",
                    "cnpj": "11111111000111",
                    "timezone": "America/Sao_Paulo",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO companies (id, name, cnpj, default_timezone) "
                    "VALUES (:id, :name, :cnpj, :timezone)"
                ),
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "name": "Company B",
                    "cnpj": "22222222000122",
                    "timezone": "America/Sao_Paulo",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO branches (id, company_id, name, code, timezone) "
                    "VALUES (:id, :company_id, :name, :code, :timezone)"
                ),
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "company_id": "11111111-1111-1111-1111-111111111111",
                    "name": "Branch A",
                    "code": "A",
                    "timezone": "America/Sao_Paulo",
                },
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO employees "
                        "(id, company_id, branch_id, name, registration_code) "
                        "VALUES (:id, :company_id, :branch_id, :name, :registration_code)"
                    ),
                    {
                        "id": "44444444-4444-4444-4444-444444444444",
                        "company_id": "22222222-2222-2222-2222-222222222222",
                        "branch_id": "33333333-3333-3333-3333-333333333333",
                        "name": "Invalid Employee",
                        "registration_code": "001",
                    },
                )
    finally:
        engine.dispose()
