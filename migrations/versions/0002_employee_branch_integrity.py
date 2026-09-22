"""Protect the relationship between an employee, branch and company."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_employee_branch_integrity"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ensure employees cannot reference a branch from another company."""

    op.create_index(
        "uq_branches_id_company",
        "branches",
        ["id", "company_id"],
        unique=True,
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER employees_company_branch_insert
                BEFORE INSERT ON employees
                FOR EACH ROW
                WHEN NOT EXISTS (
                    SELECT 1 FROM branches
                    WHERE id = NEW.branch_id AND company_id = NEW.company_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'employee branch belongs to another company');
                END
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE TRIGGER employees_company_branch_update
                BEFORE UPDATE OF branch_id, company_id ON employees
                FOR EACH ROW
                WHEN NOT EXISTS (
                    SELECT 1 FROM branches
                    WHERE id = NEW.branch_id AND company_id = NEW.company_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'employee branch belongs to another company');
                END
                """
            )
        )
    else:
        op.create_foreign_key(
            "fk_employees_branch_company",
            "employees",
            "branches",
            ["branch_id", "company_id"],
            ["id", "company_id"],
        )


def downgrade() -> None:
    """Remove the cross-entity integrity protection."""

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(sa.text("DROP TRIGGER employees_company_branch_update"))
        op.execute(sa.text("DROP TRIGGER employees_company_branch_insert"))
    else:
        op.drop_constraint("fk_employees_branch_company", "employees", type_="foreignkey")
    op.drop_index("uq_branches_id_company", table_name="branches")
