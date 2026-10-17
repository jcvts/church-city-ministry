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

    command.downgrade(config, "base")

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)

    remaining_tables = inspector.get_table_names()

    assert remaining_tables == ["alembic_version"]

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

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO rooms (
                        id,
                        name,
                        normalized_name,
                        is_active
                    )
                    VALUES (
                        :id,
                        :name,
                        :normalized_name,
                        :is_active
                    )
                    """
                ),
                {
                    "id": uuid4().hex,
                    "name": "  SALA   INFANTIL  ",
                    "normalized_name": "sala infantil",
                    "is_active": True,
                },
            )

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
