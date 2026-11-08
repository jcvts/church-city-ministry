"""add recurring service schedules

Revision ID: a55dccea784d
Revises: af76704e17ed
Create Date: 2026-11-08 01:40:39.946418

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a55dccea784d"
down_revision: str | Sequence[str] | None = "af76704e17ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_service_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=False),
        sa.Column("ends_at", sa.Time(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6",
            name="ck_recurring_schedules_weekday",
        ),
        sa.CheckConstraint(
            "ends_at > starts_at",
            name="ck_recurring_schedules_valid_time",
        ),
    )

    with op.batch_alter_table("services") as batch_op:
        batch_op.add_column(
            sa.Column(
                "recurring_schedule_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_services_recurring_schedule",
            "recurring_service_schedules",
            ["recurring_schedule_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_services_recurring_schedule_start",
            ["recurring_schedule_id", "starts_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("services") as batch_op:
        batch_op.drop_constraint(
            "uq_services_recurring_schedule_start",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_services_recurring_schedule",
            type_="foreignkey",
        )
        batch_op.drop_column("recurring_schedule_id")

    op.drop_table("recurring_service_schedules")
