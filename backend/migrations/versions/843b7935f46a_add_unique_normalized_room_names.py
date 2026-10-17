"""add unique normalized room names

Revision ID: 843b7935f46a
Revises: 6ecddf4bd644
Create Date: 2026-10-17 11:52:39.721936

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from church_city_kids.domain.scheduling import normalize_room_name

# revision identifiers, used by Alembic.
revision: str = '843b7935f46a'
down_revision: str | Sequence[str] | None = '6ecddf4bd644'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    # Validate existing data before changing the schema.
    rooms = connection.execute(
        sa.text("SELECT id, name FROM rooms")
    ).all()

    normalized_names: set[str] = set()
    updates: list[dict[str, str]] = []

    for room in rooms:
        normalized_name = normalize_room_name(room.name)

        if normalized_name in normalized_names:
            raise ValueError(
                "Cannot migrate rooms: duplicate normalized "
                f"name '{normalized_name}'"
            )

        normalized_names.add(normalized_name)
        updates.append(
            {
                "id": room.id,
                "normalized_name": normalized_name,
            }
        )

    op.add_column(
        "rooms",
        sa.Column("normalized_name", sa.String(), nullable=True),
    )

    for update in updates:
        connection.execute(
            sa.text(
                """
                UPDATE rooms
                SET normalized_name = :normalized_name
                WHERE id = :id
                """
            ),
            update,
        )

    with op.batch_alter_table("rooms") as batch_op:
        batch_op.alter_column(
            "normalized_name",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_rooms_normalized_name",
            ["normalized_name"],
        )


def downgrade() -> None:
    with op.batch_alter_table("rooms") as batch_op:
        batch_op.drop_constraint(
            "uq_rooms_normalized_name",
            type_="unique",
        )
        batch_op.drop_column("normalized_name")
