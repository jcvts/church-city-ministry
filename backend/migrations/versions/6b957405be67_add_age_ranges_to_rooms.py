"""add age ranges to rooms

Revision ID: 6b957405be67
Revises: 460e5d52a242
Create Date: 2026-11-04 00:29:03.886884

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6b957405be67'
down_revision: str | Sequence[str] | None = '460e5d52a242'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rooms",
        sa.Column("min_age_years", sa.Integer(), nullable=True),
    )
    op.add_column(
        "rooms",
        sa.Column("max_age_years", sa.Integer(), nullable=True),
    )

    with op.batch_alter_table("rooms") as batch_op:
        batch_op.create_check_constraint(
            "ck_rooms_valid_age_range",
            """
            (min_age_years IS NULL AND max_age_years IS NULL)
            OR (
                min_age_years IS NOT NULL
                AND max_age_years IS NOT NULL
                AND min_age_years >= 0
                AND max_age_years >= min_age_years
            )
            """,
        )


def downgrade() -> None:
    with op.batch_alter_table("rooms") as batch_op:
        batch_op.drop_constraint(
            "ck_rooms_valid_age_range",
            type_="check",
        )

    op.drop_column("rooms", "max_age_years")
    op.drop_column("rooms", "min_age_years")
