"""add ministry settings

Revision ID: 0dc1754e80d7
Revises: 784f187df975
Create Date: 2026-10-22 22:45:23.763209

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "0dc1754e80d7"
down_revision: str | Sequence[str] | None = "784f187df975"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create and initialize global ministry settings."""
    op.create_table(
        "ministry_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pager_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_ministry_settings_singleton",
        ),
    )

    op.execute(
        sa.text("INSERT INTO ministry_settings (id, pager_required) VALUES (1, 1)")
    )


def downgrade() -> None:
    """Remove global ministry settings."""
    op.drop_table("ministry_settings")
