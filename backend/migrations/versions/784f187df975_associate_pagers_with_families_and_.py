"""Associate pagers with families and services.

Revision ID: 784f187df975
Revises: 1ec017ee6088
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "784f187df975"
down_revision: str | Sequence[str] | None = "1ec017ee6088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    # Detect conflicting active assignments before modifying the schema.
    duplicate_families = connection.execute(
        sa.text(
            """
            SELECT children.family_id, sessions.service_id
            FROM pager_assignments
            JOIN attendances
                ON attendances.id = pager_assignments.attendance_id
            JOIN children
                ON children.id = attendances.child_id
            JOIN sessions
                ON sessions.id = attendances.session_id
            WHERE pager_assignments.released_at IS NULL
            GROUP BY children.family_id, sessions.service_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    if duplicate_families:
        raise RuntimeError(
            "Active pager assignment conflicts detected. "
            "Resolve them before migrating."
        )
    # Add nullable columns temporarily to support data migration.
    with op.batch_alter_table("pager_assignments") as batch_op:
        batch_op.add_column(sa.Column("family_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("service_id", sa.Uuid(), nullable=True))

    # Recover family and service from the original attendance relationships.
    connection.execute(
        sa.text(
            """
            UPDATE pager_assignments
            SET family_id = (
                SELECT children.family_id
                FROM attendances
                JOIN children ON children.id = attendances.child_id
                WHERE attendances.id = pager_assignments.attendance_id
            ),
            service_id = (
                SELECT sessions.service_id
                FROM attendances
                JOIN sessions ON sessions.id = attendances.session_id
                WHERE attendances.id = pager_assignments.attendance_id
            )
            """
        )
    )

    # Never silently discard historical assignments.
    missing = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM pager_assignments
            WHERE family_id IS NULL OR service_id IS NULL
            """
        )
    ).scalar_one()

    if missing:
        raise RuntimeError(
            f"Cannot migrate {missing} pager assignments: "
            "family or service could not be resolved."
        )

    # Detect conflicts before creating the unique indexes.
    duplicate_pagers = connection.execute(
        sa.text(
            """
            SELECT pager_id
            FROM pager_assignments
            WHERE released_at IS NULL
            GROUP BY pager_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    duplicate_families = connection.execute(
        sa.text(
            """
            SELECT family_id, service_id
            FROM pager_assignments
            WHERE released_at IS NULL
            GROUP BY family_id, service_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    if duplicate_pagers or duplicate_families:
        raise RuntimeError(
            "Active pager assignment conflicts detected. "
            "Resolve them before migrating."
        )

    # Rebuild the SQLite table with the new required columns and foreign keys.
    with op.batch_alter_table(
        "pager_assignments",
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s",
        },
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_pager_assignments_attendance_id",
            type_="foreignkey",
        )
        batch_op.drop_column("attendance_id")
        batch_op.alter_column(
            "family_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.alter_column(
            "service_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_pager_assignments_family_id",
            "families",
            ["family_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_pager_assignments_service_id",
            "services",
            ["service_id"],
            ["id"],
        )

    op.create_index(
        "uq_active_pager_assignment",
        "pager_assignments",
        ["pager_id"],
        unique=True,
        sqlite_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "uq_active_family_service_pager",
        "pager_assignments",
        ["family_id", "service_id"],
        unique=True,
        sqlite_where=sa.text("released_at IS NULL"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade requires an explicit data recovery plan: "
        "family-level pager assignments cannot always be mapped "
        "back to individual attendances."
    )
