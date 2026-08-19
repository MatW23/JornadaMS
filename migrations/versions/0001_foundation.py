"""Establish the initial migration baseline for the MVP-1 foundation."""

from collections.abc import Sequence

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the baseline; domain tables arrive with the next epics."""

    pass


def downgrade() -> None:
    """Remove the baseline marker."""

    pass
