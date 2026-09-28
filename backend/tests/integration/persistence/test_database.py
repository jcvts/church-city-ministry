from pathlib import Path

from sqlalchemy import text

from church_city_kids.infrastructure.persistence.database import (
    create_session_factory,
    create_sqlite_engine,
)


def test_sqlite_session_can_execute_query(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"

    engine = create_sqlite_engine(database_path)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1
    assert database_path.exists()


def test_sqlite_foreign_keys_are_enabled(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")

    with engine.connect() as connection:
        enabled = connection.execute(
            text("PRAGMA foreign_keys")
        ).scalar_one()

    assert enabled == 1
