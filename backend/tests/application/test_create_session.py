from datetime import datetime
from uuid import UUID, uuid4

import pytest

from church_city_kids.application.create_session import (
    CreateSessionRequest,
    RoomNotFoundError,
    ServiceNotFoundError,
    create_session,
)
from church_city_kids.domain.scheduling import (
    Room,
    Service,
    Session,
    SessionStatus,
)


class FakeCreateSessionRepository:
    def __init__(self, service: Service, room: Room) -> None:
        self.service = service
        self.room = room
        self.sessions: list[Session] = []
        self.added_sessions: list[Session] = []

    def get_service(self, service_id: UUID) -> Service | None:
        return self.service if self.service.id == service_id else None

    def get_room(self, room_id: UUID) -> Room | None:
        return self.room if self.room.id == room_id else None

    def get_sessions_for_service(self, service_id: UUID) -> list[Session]:
        return [
            session
            for session in self.sessions
            if session.service_id == service_id
        ]

    def add_session(self, session: Session) -> None:
        self.added_sessions.append(session)


def test_create_session_creates_scheduled_session() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 11, 19, 0),
    )
    room = Room(name="Sala Infantil")
    repository = FakeCreateSessionRepository(service, room)

    result = create_session(
        CreateSessionRequest(
            service_id=service.id,
            room_id=room.id,
            name="Infantil",
            min_age_years=3,
            max_age_years=5,
        ),
        repository,
    )

    assert len(repository.added_sessions) == 1

    session = repository.added_sessions[0]

    assert session.id == result.session_id
    assert session.service_id == service.id
    assert session.room_id == room.id
    assert session.name == "Infantil"
    assert session.min_age_years == 3
    assert session.max_age_years == 5
    assert session.status is SessionStatus.SCHEDULED


def test_create_session_rejects_unknown_service() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 11, 19, 0),
    )
    room = Room(name="Sala Infantil")
    repository = FakeCreateSessionRepository(service, room)

    request = CreateSessionRequest(
        service_id=uuid4(),
        room_id=room.id,
        name="Infantil",
        min_age_years=3,
        max_age_years=5,
    )

    with pytest.raises(ServiceNotFoundError):
        create_session(request, repository)

    assert repository.added_sessions == []


def test_create_session_rejects_unknown_room() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 11, 19, 0),
    )
    room = Room(name="Sala Infantil")
    repository = FakeCreateSessionRepository(service, room)

    request = CreateSessionRequest(
        service_id=service.id,
        room_id=uuid4(),
        name="Infantil",
        min_age_years=3,
        max_age_years=5,
    )

    with pytest.raises(RoomNotFoundError):
        create_session(request, repository)

    assert repository.added_sessions == []
