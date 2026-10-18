"""add checkout guardian to attendances

Revision ID: 1ec017ee6088
Revises: 843b7935f46a
Create Date: 2026-10-18 01:04:34.730712

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1ec017ee6088'
down_revision: str | Sequence[str] | None = '843b7935f46a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("attendances") as batch_op:
        batch_op.add_column(
            sa.Column(
                "checked_out_by_guardian_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_attendances_checked_out_by_guardian_id",
            "guardians",
            ["checked_out_by_guardian_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("attendances") as batch_op:
        batch_op.drop_constraint(
            "fk_attendances_checked_out_by_guardian_id",
            type_="foreignkey",
        )
        batch_op.drop_column("checked_out_by_guardian_id")
