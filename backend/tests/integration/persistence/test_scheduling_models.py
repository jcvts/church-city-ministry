from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    RoomModel,
    ServiceModel,
    SessionModel,
)


def test_service_end_must_be_after_start(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    starts_at = datetime(2026, 9, 20, 19, 0)

    with Session(engine) as session:
        session.add(
            ServiceModel(
                id=uuid4(),
                name="Sunday Service",
                starts_at=starts_at,
                ends_at=starts_at,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_session_rejects_invalid_age_range(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()

    with Session(engine) as session:
        session.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 9, 20, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=uuid4(),
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=6,
                max_age_years=5,
                status="SCHEDULED",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_room_cannot_have_two_sessions_in_same_service(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()

    with Session(engine) as session:
        session.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 9, 20, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add_all(
            [
                SessionModel(
                    id=uuid4(),
                    service_id=service_id,
                    room_id=room_id,
                    name="Kids A",
                    min_age_years=3,
                    max_age_years=5,
                    status="SCHEDULED",
                ),
                SessionModel(
                    id=uuid4(),
                    service_id=service_id,
                    room_id=room_id,
                    name="Kids B",
                    min_age_years=6,
                    max_age_years=11,
                    status="SCHEDULED",
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()
