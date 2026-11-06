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
    VolunteerAssignmentModel,
    VolunteerModel,
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


def test_volunteer_deactivation_preserves_existing_assignments(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    volunteer_id = uuid4()

    with Session(engine) as db:
        db.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 11, 8, 10, 0),
                ends_at=None,
            )
        )
        db.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        db.add(
            VolunteerModel(
                id=volunteer_id,
                full_name="Maria Oliveira",
                is_active=True,
            )
        )
        db.flush()

        db.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="SCHEDULED",
            )
        )
        db.flush()

        db.add(
            VolunteerAssignmentModel(
                id=uuid4(),
                service_id=service_id,
                session_id=session_id,
                volunteer_id=volunteer_id,
                role=None,
            )
        )
        db.commit()

        volunteer = db.get(VolunteerModel, volunteer_id)
        assert volunteer is not None
        volunteer.is_active = False
        db.commit()

        db.expire_all()

        assignment = db.query(VolunteerAssignmentModel).one()
        saved_volunteer = db.get(VolunteerModel, volunteer_id)

        assert assignment.volunteer_id == volunteer_id
        assert saved_volunteer is not None
        assert saved_volunteer.is_active is False

    engine.dispose()


def test_volunteer_cannot_be_assigned_twice_in_same_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    volunteer_id = uuid4()
    room_ids = [uuid4(), uuid4()]
    session_ids = [uuid4(), uuid4()]

    with Session(engine) as db:
        db.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 11, 8, 10, 0),
                ends_at=None,
            )
        )
        db.add(
            VolunteerModel(
                id=volunteer_id,
                full_name="Maria Oliveira",
                is_active=True,
            )
        )
        db.add_all(
            [
                RoomModel(
                    id=room_id,
                    name=f"Room {index}",
                    is_active=True,
                )
                for index, room_id in enumerate(room_ids)
            ]
        )
        db.flush()

        db.add_all(
            [
                SessionModel(
                    id=session_id,
                    service_id=service_id,
                    room_id=room_id,
                    name=f"Kids {index}",
                    min_age_years=3,
                    max_age_years=5,
                    status="SCHEDULED",
                )
                for index, (session_id, room_id) in enumerate(
                    zip(session_ids, room_ids)
                )
            ]
        )
        db.flush()

        db.add(
            VolunteerAssignmentModel(
                id=uuid4(),
                service_id=service_id,
                session_id=session_ids[0],
                volunteer_id=volunteer_id,
            )
        )
        db.commit()

        db.add(
            VolunteerAssignmentModel(
                id=uuid4(),
                service_id=service_id,
                session_id=session_ids[1],
                volunteer_id=volunteer_id,
            )
        )

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

    engine.dispose()
