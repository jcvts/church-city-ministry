from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from church_city_kids.application.create_session import (
    CreateSessionRequest,
    create_session,
)
from church_city_kids.domain.errors import RoomAlreadyAssignedInServiceError
from church_city_kids.domain.scheduling import Session as DomainSession
from church_city_kids.domain.scheduling import SessionStatus
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    Base,
    RoomModel,
    ServiceModel,
    SessionModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyCreateSessionRepository,
)


def test_get_service_returns_domain_service(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    starts_at = datetime(2026, 10, 11, 19, 0)

    with DbSession(engine) as db_session:
        db_session.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=starts_at,
                ends_at=None,
            )
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        service = repository.get_service(service_id)

        assert service is not None
        assert service.id == service_id
        assert service.name == "Sunday Service"
        assert service.starts_at == starts_at
        assert service.ends_at is None

    engine.dispose()


def test_get_room_returns_domain_room(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    room_id = uuid4()

    with DbSession(engine) as db_session:
        db_session.add(
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=False,
            )
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        room = repository.get_room(room_id)

        assert room is not None
        assert room.id == room_id
        assert room.name == "Sala Infantil"
        assert room.is_active is False

    engine.dispose()


def test_get_sessions_for_service_returns_only_matching_sessions(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    first_service_id = uuid4()
    second_service_id = uuid4()
    first_room_id = uuid4()
    second_room_id = uuid4()

    with DbSession(engine) as db_session:
        db_session.add_all(
            [
                ServiceModel(
                    id=first_service_id,
                    name="Sunday Morning",
                    starts_at=datetime(2026, 10, 11, 9, 0),
                    ends_at=None,
                ),
                ServiceModel(
                    id=second_service_id,
                    name="Sunday Evening",
                    starts_at=datetime(2026, 10, 11, 19, 0),
                    ends_at=None,
                ),
                RoomModel(
                    id=first_room_id,
                    name="Sala Infantil",
                    is_active=True,
                ),
                RoomModel(
                    id=second_room_id,
                    name="Sala Kids",
                    is_active=True,
                ),
            ]
        )
        db_session.flush()

        first_session_id = uuid4()

        db_session.add_all(
            [
                SessionModel(
                    id=first_session_id,
                    service_id=first_service_id,
                    room_id=first_room_id,
                    name="Infantil",
                    min_age_years=3,
                    max_age_years=5,
                    status="scheduled",
                ),
                SessionModel(
                    id=uuid4(),
                    service_id=second_service_id,
                    room_id=second_room_id,
                    name="Kids",
                    min_age_years=6,
                    max_age_years=11,
                    status="open",
                ),
            ]
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        sessions = repository.get_sessions_for_service(first_service_id)

        assert len(sessions) == 1

        session = sessions[0]

        assert session.id == first_session_id
        assert session.service_id == first_service_id
        assert session.room_id == first_room_id
        assert session.name == "Infantil"
        assert session.min_age_years == 3
        assert session.max_age_years == 5
        assert session.status is SessionStatus.SCHEDULED

    engine.dispose()


def test_add_session_persists_session_without_committing(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()

    with DbSession(engine) as db_session:
        db_session.add(
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 11, 19, 0),
                ends_at=None,
            )
        )
        db_session.add(
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=True,
            )
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        domain_session = DomainSession(
            service_id=service_id,
            room_id=room_id,
            name="Infantil",
            min_age_years=3,
            max_age_years=5,
        )

        repository.add_session(domain_session)

        # The repository must not commit the transaction.
        assert db_session.in_transaction()

        # Flush pending changes so they can be queried.
        db_session.flush()

        model = db_session.get(SessionModel, domain_session.id)

        assert model is not None
        assert model.id == domain_session.id
        assert model.service_id == service_id
        assert model.room_id == room_id
        assert model.name == "Infantil"
        assert model.min_age_years == 3
        assert model.max_age_years == 5
        assert model.status == SessionStatus.SCHEDULED.value

        # Roll back the uncommitted changes.
        db_session.rollback()

        assert db_session.get(SessionModel, domain_session.id) is None

    engine.dispose()


def test_create_session_use_case_persists_session(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()

    with DbSession(engine) as db_session:
        db_session.add_all(
            [
                ServiceModel(
                    id=service_id,
                    name="Sunday Service",
                    starts_at=datetime(2026, 10, 11, 19, 0),
                    ends_at=None,
                ),
                RoomModel(
                    id=room_id,
                    name="Sala Infantil",
                    is_active=True,
                ),
            ]
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        result = create_session(
            CreateSessionRequest(
                service_id=service_id,
                room_id=room_id,
                name="Infantil",
                min_age_years=3,
                max_age_years=5,
            ),
            repository,
        )

        # The transaction is controlled outside the repository.
        db_session.commit()

    # A new database session proves the data was committed.
    with DbSession(engine) as verification_session:
        model = verification_session.get(
            SessionModel,
            result.session_id,
        )

        assert model is not None
        assert model.service_id == service_id
        assert model.room_id == room_id
        assert model.name == "Infantil"
        assert model.min_age_years == 3
        assert model.max_age_years == 5
        assert model.status == SessionStatus.SCHEDULED.value

    engine.dispose()


def test_create_session_rejects_duplicate_room_in_same_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    service_id = uuid4()
    room_id = uuid4()

    with DbSession(engine) as db_session:
        db_session.add_all(
            [
                ServiceModel(
                    id=service_id,
                    name="Sunday Service",
                    starts_at=datetime(2026, 10, 11, 19, 0),
                    ends_at=None,
                ),
                RoomModel(
                    id=room_id,
                    name="Sala Infantil",
                    is_active=True,
                ),
            ]
        )
        db_session.commit()

        repository = SqlAlchemyCreateSessionRepository(db_session)

        first_request = CreateSessionRequest(
            service_id=service_id,
            room_id=room_id,
            name="Infantil",
            min_age_years=3,
            max_age_years=5,
        )

        first_result = create_session(first_request, repository)
        db_session.commit()

        duplicate_request = CreateSessionRequest(
            service_id=service_id,
            room_id=room_id,
            name="Outra Turma",
            min_age_years=6,
            max_age_years=11,
        )

        with pytest.raises(RoomAlreadyAssignedInServiceError):
            create_session(duplicate_request, repository)

        db_session.rollback()

    with DbSession(engine) as verification_session:
        sessions = verification_session.scalars(
            select(SessionModel).where(
                SessionModel.service_id == service_id
            )
        ).all()

        assert len(sessions) == 1
        assert sessions[0].id == first_result.session_id
        assert sessions[0].name == "Infantil"

    engine.dispose()
