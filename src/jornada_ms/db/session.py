"""Database engine construction and readiness checks."""

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from jornada_ms.config import Settings


class DatabaseUnavailable(RuntimeError):
    """Raised when the configured database cannot answer a readiness check."""


@dataclass(slots=True)
class Database:
    """Small infrastructure wrapper kept outside the domain layer."""

    engine: Engine

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        return cls(engine=engine)

    def check(self) -> None:
        """Run a minimal query used by the readiness endpoint."""

        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - exact driver exception varies
            raise DatabaseUnavailable("database readiness check failed") from exc

    def dispose(self) -> None:
        """Release pooled connections during application shutdown or tests."""

        self.engine.dispose()
