from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_PATH = Path("church_city_kids.db")


def create_sqlite_engine(database_path: Path = DEFAULT_DATABASE_PATH) -> Engine:
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: DBAPIConnection,
        connection_record: object,
    ) -> None:
        del connection_record

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(
    session_factory: sessionmaker[Session],
) -> Iterator[Session]:
    with session_factory() as session:
        yield session