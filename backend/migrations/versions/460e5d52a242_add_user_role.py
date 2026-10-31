"""Add user role.

Revision ID: 460e5d52a242
Revises: 43e33513f120
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "460e5d52a242"
down_revision: str | None = "43e33513f120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="volunteer",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")