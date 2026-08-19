"""SQLAlchemy declarative base shared by application models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future JornadaMS ORM models."""
