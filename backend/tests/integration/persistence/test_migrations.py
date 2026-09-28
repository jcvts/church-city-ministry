from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
