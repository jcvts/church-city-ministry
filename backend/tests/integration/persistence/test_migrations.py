from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def test_migrations_create_expected_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "migration_test.db"

    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path}",
    )

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "attendances",
        "child_guardians",
        "children",
        "families",
        "guardians",
        "pager_assignments",
        "pagers",
        "rooms",
        "services",
        "sessions",
        "volunteer_assignments",
        "volunteers",
    }

    engine.dispose()

    # The latest pager migration intentionally blocks automatic downgrade.
    with pytest.raises(
        RuntimeError,
        match="Downgrade requires an explicit data recovery plan",
    ):
        command.downgrade(config, "base")


def test_previous_migrations_can_downgrade_to_base(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy_downgrade_test.db"
    database_url = f"sqlite:///{database_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    # Stop before the irreversible family-level pager migration.
    command.upgrade(config, "1ec017ee6088")

    engine = create_engine(database_url)
    assert "pager_assignments" in inspect(engine).get_table_names()
    engine.dispose()

    # Previous migrations remain reversible.
    command.downgrade(config, "base")

    engine = create_engine(database_url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_room_name_uniqueness_migration_preserves_existing_data(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "room_migration_test.db"
    database_url = f"sqlite:///{database_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "6ecddf4bd644")

    engine = create_engine(database_url)
    room_id = uuid4().hex

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO rooms (id, name, is_active)
                VALUES (:id, :name, :is_active)
                """
            ),
            {
                "id": room_id,
                "name": "Sala Infantil",
                "is_active": True,
            },
        )

    engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)

    with engine.connect() as connection:
        room = connection.execute(
            text(
                """
                SELECT id, name, normalized_name
                FROM rooms
                WHERE id = :id
                """
            ),
            {"id": room_id},
        ).one()

        assert room.name == "Sala Infantil"
        assert room.normalized_name == "sala infantil"

    engine.dispose()


def test_room_name_migration_rejects_existing_duplicates(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "duplicate_rooms_migration.db"
    database_url = f"sqlite:///{database_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "6ecddf4bd644")

    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO rooms (id, name, is_active)
                VALUES (:id, :name, :is_active)
                """
            ),
            [
                {
                    "id": uuid4().hex,
                    "name": "Sala Infantil",
                    "is_active": True,
                },
                {
                    "id": uuid4().hex,
                    "name": "  SALA   INFANTIL  ",
                    "is_active": True,
                },
            ],
        )

    engine.dispose()

    with pytest.raises(
        ValueError,
        match="duplicate normalized name 'sala infantil'",
    ):
        command.upgrade(config, "head")

    engine = create_engine(database_url)

    with engine.connect() as connection:
        names = connection.execute(
            text("SELECT name FROM rooms ORDER BY name")
        ).scalars().all()

        columns = {
            column["name"]
            for column in inspect(connection).get_columns("rooms")
        }

    assert names == [
        "  SALA   INFANTIL  ",
        "Sala Infantil",
    ]
    assert "normalized_name" not in columns

    engine.dispose()


def test_checkout_guardian_migration_preserves_existing_attendances(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "checkout_guardian_migration.db"
    database_url = f"sqlite:///{database_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    # Start from the revision before the checkout guardian column.
    command.upgrade(config, "843b7935f46a")

    engine = create_engine(database_url)

    attendance_id = uuid4().hex
    child_id = uuid4().hex
    family_id = uuid4().hex
    service_id = uuid4().hex
    room_id = uuid4().hex
    session_id = uuid4().hex

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO families (id, is_active)
                VALUES (:id, :is_active)
                """
            ),
            {"id": family_id, "is_active": True},
        )

        connection.execute(
            text(
                """
                INSERT INTO children (
                    id, family_id, full_name, birth_date, is_active
                )
                VALUES (
                    :id, :family_id, :full_name, :birth_date, :is_active
                )
                """
            ),
            {
                "id": child_id,
                "family_id": family_id,
                "full_name": "Test Child",
                "birth_date": "2021-01-01",
                "is_active": True,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO services (id, name, starts_at, ends_at)
                VALUES (:id, :name, :starts_at, NULL)
                """
            ),
            {
                "id": service_id,
                "name": "Sunday Service",
                "starts_at": "2026-10-04 19:00:00",
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO rooms (id, name, normalized_name, is_active)
                VALUES (:id, :name, :normalized_name, :is_active)
                """
            ),
            {
                "id": room_id,
                "name": "Kids Room",
                "normalized_name": "kids room",
                "is_active": True,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO sessions (
                    id, service_id, room_id, name,
                    min_age_years, max_age_years, status
                )
                VALUES (
                    :id, :service_id, :room_id, :name,
                    :min_age_years, :max_age_years, :status
                )
                """
            ),
            {
                "id": session_id,
                "service_id": service_id,
                "room_id": room_id,
                "name": "Kids 3-5",
                "min_age_years": 3,
                "max_age_years": 5,
                "status": "OPEN",
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO attendances (
                    id, child_id, session_id,
                    checked_in_at, checked_out_at
                )
                VALUES (
                    :id, :child_id, :session_id,
                    :checked_in_at, :checked_out_at
                )
                """
            ),
            {
                "id": attendance_id,
                "child_id": child_id,
                "session_id": session_id,
                "checked_in_at": "2026-10-04 18:30:00",
                "checked_out_at": "2026-10-04 20:00:00",
            },
        )

    engine.dispose()

    # Apply the new migration to an existing attendance.
    command.upgrade(config, "1ec017ee6088")

    engine = create_engine(database_url)

    with engine.connect() as connection:
        attendance = connection.execute(
            text(
                """
                SELECT id, checked_out_at, checked_out_by_guardian_id
                FROM attendances
                WHERE id = :id
                """
            ),
            {"id": attendance_id},
        ).one()

        assert attendance.id == attendance_id
        assert attendance.checked_out_at is not None
        assert attendance.checked_out_by_guardian_id is None

        columns = {
            column["name"]
            for column in inspect(connection).get_columns("attendances")
        }

        assert "checked_out_by_guardian_id" in columns

        connection.exec_driver_sql("PRAGMA foreign_keys=ON")

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        """
                        UPDATE attendances
                        SET checked_out_by_guardian_id = :guardian_id
                        WHERE id = :attendance_id
                        """
                    ),
                    {
                        "guardian_id": uuid4().hex,
                        "attendance_id": attendance_id,
                    },
                )

        foreign_keys = inspect(connection).get_foreign_keys("attendances")

        assert any(
            fk["referred_table"] == "guardians"
            and fk["constrained_columns"] == ["checked_out_by_guardian_id"]
            and fk["referred_columns"] == ["id"]
            for fk in foreign_keys
        )

    engine.dispose()

    # Revert only the checkout guardian migration.
    command.downgrade(config, "843b7935f46a")

    engine = create_engine(database_url)

    with engine.connect() as connection:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("attendances")
        }

        assert "checked_out_by_guardian_id" not in columns

        attendance = connection.execute(
            text(
                """
                SELECT id, checked_out_at
                FROM attendances
                WHERE id = :id
                """
            ),
            {"id": attendance_id},
        ).one()

        assert attendance.id == attendance_id
        assert attendance.checked_out_at is not None

    engine.dispose()
