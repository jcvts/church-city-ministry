from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session as DbSession

from church_city_kids.application.assign_volunteer import (
    AssignVolunteerRequest,
    assign_volunteer,
)
from church_city_kids.application.list_volunteer_assignments import (
    ServiceNotFoundError,
    list_volunteer_assignments,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    ServiceModel,
    SessionModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyAssignVolunteerRepository,
    SqlAlchemyListVolunteerAssignmentsRepository,
)
from tests.integration.persistence.test_assign_volunteer_repository import (
    seed_service,
)


def test_list_assignments_includes_volunteer_names_and_roles(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    try:
        with DbSession(engine) as db:
            service_id, session_ids, volunteer_ids = seed_service(db)
            assignment_repository = SqlAlchemyAssignVolunteerRepository(db)

            assign_volunteer(
                AssignVolunteerRequest(
                    session_id=session_ids[0],
                    volunteer_id=volunteer_ids[0],
                    role="Teacher",
                ),
                assignment_repository,
            )
            assign_volunteer(
                AssignVolunteerRequest(
                    session_id=session_ids[1],
                    volunteer_id=volunteer_ids[1],
                ),
                assignment_repository,
            )
            db.commit()

            repository = SqlAlchemyListVolunteerAssignmentsRepository(db)
            results = list_volunteer_assignments(service_id, repository)

            assert len(results) == 2
            assert {item.session_id for item in results} == set(session_ids)
            assert {item.volunteer_name for item in results} == {
                "Volunteer 1",
                "Volunteer 2",
            }
            assert {item.role for item in results} == {"Teacher", None}
            assert all(item.service_id == service_id for item in results)
    finally:
        engine.dispose()


def test_list_assignments_returns_empty_for_service_without_assignments(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    try:
        with DbSession(engine) as db:
            service_id, _, _ = seed_service(db)
            repository = SqlAlchemyListVolunteerAssignmentsRepository(db)

            assert list_volunteer_assignments(service_id, repository) == []
    finally:
        engine.dispose()


def test_list_assignments_rejects_unknown_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    try:
        with DbSession(engine) as db:
            repository = SqlAlchemyListVolunteerAssignmentsRepository(db)

            try:
                list_volunteer_assignments(uuid4(), repository)
                assert False, "Expected ServiceNotFoundError"
            except ServiceNotFoundError:
                pass
    finally:
        engine.dispose()


def test_list_assignments_does_not_mix_services(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    try:
        with DbSession(engine) as db:
            first_service_id, first_sessions, volunteer_ids = seed_service(db)

            second_service_id = uuid4()
            second_session_id = uuid4()

            first_session = db.get(SessionModel, first_sessions[0])
            assert first_session is not None

            db.add(
                ServiceModel(
                    id=second_service_id,
                    name="Evening Service",
                    starts_at=datetime(2026, 11, 8, 19, 0),
                    ends_at=None,
                )
            )
            db.flush()

            db.add(
                SessionModel(
                    id=second_session_id,
                    service_id=second_service_id,
                    room_id=first_session.room_id,
                    name="Evening Kids",
                    min_age_years=3,
                    max_age_years=5,
                    status="scheduled",
                )
            )
            db.commit()

            assignment_repository = SqlAlchemyAssignVolunteerRepository(db)

            first_assignment = assign_volunteer(
                AssignVolunteerRequest(
                    session_id=first_sessions[0],
                    volunteer_id=volunteer_ids[0],
                ),
                assignment_repository,
            )

            second_assignment = assign_volunteer(
                AssignVolunteerRequest(
                    session_id=second_session_id,
                    volunteer_id=volunteer_ids[0],
                ),
                assignment_repository,
            )
            db.commit()

            repository = SqlAlchemyListVolunteerAssignmentsRepository(db)

            first_results = list_volunteer_assignments(first_service_id, repository)
            second_results = list_volunteer_assignments(second_service_id, repository)

            assert len(first_results) == 1
            assert first_results[0].assignment_id == first_assignment.assignment_id
            assert first_results[0].session_id == first_sessions[0]

            assert len(second_results) == 1
            assert second_results[0].assignment_id == second_assignment.assignment_id
            assert second_results[0].session_id == second_session_id

            assert first_results[0].volunteer_id == second_results[0].volunteer_id
    finally:
        engine.dispose()
