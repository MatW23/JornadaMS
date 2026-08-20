import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

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
    finally:
        engine.dispose()

    run_alembic("downgrade", "base", database_url, repository)
    engine = create_engine(database_url)
    try:
        assert not CORE_TABLES.intersection(set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
