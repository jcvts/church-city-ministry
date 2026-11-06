from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from church_city_kids.application.update_room import (
    UpdateRoomRequest,
    update_room,
)
from church_city_kids.domain.scheduling import Room
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
    SqlAlchemyUpdateRoomRepository,
)


def test_update_room_repository_returns_room(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    room = Room(
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
    )

    with Session(engine) as session:
        session.add(
            RoomModel(
                id=room.id,
                name=room.name,
                normalized_name="sala 1",
                is_active=True,
                min_age_years=3,
                max_age_years=5,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateRoomRepository(session)

        result = repository.get_room(room.id)

        assert result is not None
        assert result.id == room.id
        assert result.name == "Sala 1"
        assert result.min_age_years == 3
        assert result.max_age_years == 5

    engine.dispose()


def test_update_room_repository_returns_none_for_missing_room(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SqlAlchemyUpdateRoomRepository(session)

        assert repository.get_room(uuid4()) is None

    engine.dispose()


def test_update_room_repository_detects_duplicate_name(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    room = Room(name="Sala Infantil")

    with Session(engine) as session:
        session.add(
            RoomModel(
                id=room.id,
                name=room.name,
                normalized_name="sala infantil",
                is_active=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateRoomRepository(session)

        assert repository.room_name_exists(
            "  SALA   INFANTIL  ",
            uuid4(),
        )

        assert not repository.room_name_exists(
            "Sala Infantil",
            room.id,
        )

    engine.dispose()


def test_update_room_repository_persists_changes(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    room = Room(
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
    )

    with Session(engine) as session:
        session.add(
            RoomModel(
                id=room.id,
                name=room.name,
                normalized_name="sala 1",
                is_active=True,
                min_age_years=3,
                max_age_years=5,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateRoomRepository(session)

        update_room(
            UpdateRoomRequest(
                room_id=room.id,
                name="Berçário",
                min_age_years=2,
                max_age_years=3,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        saved_room = session.get(RoomModel, room.id)

        assert saved_room is not None
        assert saved_room.name == "Berçário"
        assert saved_room.normalized_name == "berçário"
        assert saved_room.min_age_years == 2
        assert saved_room.max_age_years == 3
        assert saved_room.is_active is True

    engine.dispose()


def test_update_room_does_not_change_existing_sessions(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    room = Room(
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
    )

    service_id = uuid4()
    session_id = uuid4()

    with Session(engine) as session:
        session.add_all(
            [
                ServiceModel(
                    id=service_id,
                    name="Culto de Domingo",
                    starts_at=datetime(2026, 11, 22, 9, 0),
                ),
                RoomModel(
                    id=room.id,
                    name=room.name,
                    normalized_name="sala 1",
                    is_active=True,
                    min_age_years=3,
                    max_age_years=5,
                ),
            ]
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room.id,
                name="Sala 1",
                min_age_years=3,
                max_age_years=5,
                status="scheduled",
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateRoomRepository(session)

        update_room(
            UpdateRoomRequest(
                room_id=room.id,
                name="Sala Infantil",
                min_age_years=2,
                max_age_years=6,
            ),
            repository,
        )
        session.commit()

    with Session(engine) as session:
        saved_session = session.get(SessionModel, session_id)

        assert saved_session is not None
        assert saved_session.name == "Sala 1"
        assert saved_session.min_age_years == 3
        assert saved_session.max_age_years == 5

    engine.dispose()
