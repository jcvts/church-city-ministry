from collections.abc import Generator
from pathlib import Path

from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)

engine = create_sqlite_engine(Path("church_city_kids.db"))


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
