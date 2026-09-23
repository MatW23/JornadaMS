"""Add auditable attendance adjustment requests."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_adjustment_workflow"
down_revision: str | None = "0002_employee_branch_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add event lifecycle status and the approval workflow."""

    op.add_column(
        "time_events",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="VALID"),
    )
    op.create_table(
        "adjustment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("target_event_id", sa.Uuid(), nullable=True),
        sa.Column("proposed_event_type", sa.String(length=32), nullable=False),
        sa.Column("proposed_occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposed_timezone", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decision_comment", sa.String(length=1000), nullable=True),
        sa.Column("result_event_id", sa.Uuid(), nullable=True),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_adjustment_requests_employee_date",
        "adjustment_requests",
        ["employee_id", "work_date"],
    )
    op.create_index(
        "ix_adjustment_requests_status",
        "adjustment_requests",
        ["status"],
    )


def downgrade() -> None:
    """Remove the adjustment workflow."""

    op.drop_index("ix_adjustment_requests_status", table_name="adjustment_requests")
    op.drop_index("ix_adjustment_requests_employee_date", table_name="adjustment_requests")
    op.drop_table("adjustment_requests")
    op.drop_column("time_events", "status")
