"""enforce volunteer assignment per service

Revision ID: af76704e17ed
Revises: 6b957405be67
Create Date: 2026-11-04 23:42:21.715181
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "af76704e17ed"
down_revision: str | Sequence[str] | None = "6b957405be67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    # Verify existing assignments before changing the schema.
    duplicates = connection.execute(
        sa.text(
            """
            SELECT s.service_id, va.volunteer_id
            FROM volunteer_assignments va
            JOIN sessions s ON s.id = va.session_id
            GROUP BY s.service_id, va.volunteer_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    if duplicates:
        raise RuntimeError("Duplicate volunteer assignments detected within a service.")

    op.create_index(
        "uq_sessions_id_service",
        "sessions",
        ["id", "service_id"],
        unique=True,
    )

    # Add service_id temporarily as nullable.
    with op.batch_alter_table("volunteer_assignments") as batch_op:
        batch_op.add_column(sa.Column("service_id", sa.Uuid(), nullable=True))

    # Derive service_id from the associated session.
    connection.execute(
        sa.text(
            """
            UPDATE volunteer_assignments
            SET service_id = (
                SELECT service_id
                FROM sessions
                WHERE sessions.id = volunteer_assignments.session_id
            )
            """
        )
    )

    missing = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM volunteer_assignments
            WHERE service_id IS NULL
            """
        )
    ).scalar_one()

    if missing:
        raise RuntimeError(f"Cannot migrate {missing} assignments without a service.")

    # Rebuild with the new foreign key and uniqueness constraint.
    with op.batch_alter_table(
        "volunteer_assignments",
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s",
        },
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_volunteer_assignments_session_id",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "service_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_volunteer_assignments_service_id",
            "services",
            ["service_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_volunteer_assignments_session_service",
            "sessions",
            ["session_id", "service_id"],
            ["id", "service_id"],
        )
        batch_op.create_unique_constraint(
            "uq_volunteer_assignments_service_volunteer",
            ["service_id", "volunteer_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "uq_sessions_id_service",
        table_name="sessions",
    )
    with op.batch_alter_table(
        "volunteer_assignments",
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s",
        },
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_volunteer_assignments_service_volunteer",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_volunteer_assignments_session_service",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_volunteer_assignments_service_id",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_volunteer_assignments_session_id",
            "sessions",
            ["session_id"],
            ["id"],
        )
        batch_op.drop_column("service_id")
