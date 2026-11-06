from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from church_city_kids.application.assign_volunteer import (
    AssignVolunteerRequest,
    assign_volunteer,
)
from church_city_kids.domain.errors import (
    VolunteerAlreadyAssignedInServiceError,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    RoomModel,
    ServiceModel,
    SessionModel,
    VolunteerAssignmentModel,
    VolunteerModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyAssignVolunteerRepository,
)


def seed_service(db: DbSession) -> tuple:
    service_id = uuid4()
    session_ids = [uuid4(), uuid4()]
    volunteer_ids = [uuid4(), uuid4()]

    db.add(
        ServiceModel(
            id=service_id,
            name="Sunday Service",
            starts_at=datetime(2026, 11, 8, 10, 0),
            ends_at=None,
        )
    )

    room_ids = [uuid4(), uuid4()]
    for index, room_id in enumerate(room_ids):
        db.add(
            RoomModel(
                id=room_id,
                name=f"Room {index + 1}",
                is_active=True,
            )
        )

    for index, volunteer_id in enumerate(volunteer_ids):
        db.add(
            VolunteerModel(
                id=volunteer_id,
                full_name=f"Volunteer {index + 1}",
                is_active=True,
            )
        )

    db.flush()

    for index, session_id in enumerate(session_ids):
        db.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_ids[index],
                name=f"Kids Room {index + 1}",
                min_age_years=3 if index == 0 else 6,
                max_age_years=5 if index == 0 else 11,
                status="SCHEDULED",
            )
        )

    db.commit()

    return service_id, session_ids, volunteer_ids


def test_repository_loads_session_and_volunteer(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        service_id, session_ids, volunteer_ids = seed_service(db)
        repository = SqlAlchemyAssignVolunteerRepository(db)

        session = repository.get_session(session_ids[0])
        volunteer = repository.get_volunteer(volunteer_ids[0])

        assert session is not None
        assert session.service_id == service_id
        assert volunteer is not None
        assert volunteer.full_name == "Volunteer 1"

        assert repository.get_session(uuid4()) is None
        assert repository.get_volunteer(uuid4()) is None

    engine.dispose()


def test_assignment_is_persisted_and_reloaded(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        service_id, session_ids, volunteer_ids = seed_service(db)
        repository = SqlAlchemyAssignVolunteerRepository(db)

        result = assign_volunteer(
            AssignVolunteerRequest(
                session_id=session_ids[0],
                volunteer_id=volunteer_ids[0],
                role="Teacher",
            ),
            repository,
        )
        db.commit()

    with DbSession(engine) as db:
        repository = SqlAlchemyAssignVolunteerRepository(db)
        assignments = repository.get_assignments_for_service(service_id)

        assert len(assignments) == 1
        assert assignments[0].id == result.assignment_id
        assert assignments[0].session_id == session_ids[0]
        assert assignments[0].volunteer_id == volunteer_ids[0]
        assert assignments[0].role == "Teacher"

    engine.dispose()


def test_repository_filters_assignments_by_service(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        first_service_id, first_sessions, volunteers = seed_service(db)

        repository = SqlAlchemyAssignVolunteerRepository(db)
        assign_volunteer(
            AssignVolunteerRequest(
                session_id=first_sessions[0],
                volunteer_id=volunteers[0],
            ),
            repository,
        )

        second_service_id = uuid4()
        second_session_id = uuid4()
        second_room_id = uuid4()

        db.add(
            ServiceModel(
                id=second_service_id,
                name="Evening Service",
                starts_at=datetime(2026, 11, 8, 19, 0),
                ends_at=None,
            )
        )
        db.add(
            RoomModel(
                id=second_room_id,
                name="Evening Room",
                is_active=True,
            )
        )
        db.flush()

        db.add(
            SessionModel(
                id=second_session_id,
                service_id=second_service_id,
                room_id=second_room_id,
                name="Evening Kids",
                min_age_years=3,
                max_age_years=11,
                status="SCHEDULED",
            )
        )
        db.flush()

        assign_volunteer(
            AssignVolunteerRequest(
                session_id=second_session_id,
                volunteer_id=volunteers[0],
            ),
            repository,
        )
        db.commit()

        assert len(repository.get_assignments_for_service(first_service_id)) == 1
        assert len(repository.get_assignments_for_service(second_service_id)) == 1

    engine.dispose()


def test_use_case_rejects_duplicate_in_same_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        service_id, session_ids, volunteer_ids = seed_service(db)
        repository = SqlAlchemyAssignVolunteerRepository(db)

        assign_volunteer(
            AssignVolunteerRequest(
                session_id=session_ids[0],
                volunteer_id=volunteer_ids[0],
            ),
            repository,
        )
        db.commit()

        with pytest.raises(VolunteerAlreadyAssignedInServiceError):
            assign_volunteer(
                AssignVolunteerRequest(
                    session_id=session_ids[1],
                    volunteer_id=volunteer_ids[0],
                ),
                repository,
            )

        assert len(repository.get_assignments_for_service(service_id)) == 1

    engine.dispose()


def test_database_rejects_duplicate_even_without_use_case(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        service_id, session_ids, volunteer_ids = seed_service(db)

        db.add_all(
            [
                VolunteerAssignmentModel(
                    id=uuid4(),
                    service_id=service_id,
                    session_id=session_ids[0],
                    volunteer_id=volunteer_ids[0],
                    role=None,
                ),
                VolunteerAssignmentModel(
                    id=uuid4(),
                    service_id=service_id,
                    session_id=session_ids[1],
                    volunteer_id=volunteer_ids[0],
                    role=None,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            db.commit()

    engine.dispose()
