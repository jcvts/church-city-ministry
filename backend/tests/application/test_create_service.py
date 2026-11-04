from datetime import datetime

import pytest

from church_city_kids.application.create_service import (
    CreateServiceRequest,
    create_service,
)
from church_city_kids.domain.scheduling import (
    Room,
    Service,
    Session,
)


class FakeCreateServiceRepository:
    def __init__(self, rooms: list[Room]) -> None:
        self.rooms = rooms
        self.added_services: list[Service] = []
        self.added_sessions: list[Session] = []

    def get_active_rooms(self) -> list[Room]:
        return [room for room in self.rooms if room.is_active]

    def add_service(self, service: Service) -> None:
        self.added_services.append(service)

    def add_session(self, session: Session) -> None:
        self.added_sessions.append(session)


def test_create_service_creates_service_and_sessions_for_active_rooms() -> None:
    nursery = Room(
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
    )
    children = Room(
        name="Sala 2",
        min_age_years=6,
        max_age_years=11,
    )
    inactive_room = Room(
        name="Sala desativada",
        is_active=False,
        min_age_years=12,
        max_age_years=14,
    )

    repository = FakeCreateServiceRepository(
        rooms=[nursery, children, inactive_room],
    )

    request = CreateServiceRequest(
        name="Culto 22/11/2026",
        starts_at=datetime(2026, 11, 22, 9, 0),
    )

    result = create_service(request, repository)

    assert len(repository.added_services) == 1
    assert len(repository.added_sessions) == 2

    service = repository.added_services[0]

    assert service.id == result.service_id
    assert service.name == "Culto 22/11/2026"

    sessions_by_room = {
        session.room_id: session
        for session in repository.added_sessions
    }

    assert sessions_by_room[nursery.id].service_id == service.id
    assert sessions_by_room[nursery.id].name == nursery.name
    assert sessions_by_room[nursery.id].min_age_years == 3
    assert sessions_by_room[nursery.id].max_age_years == 5

    assert sessions_by_room[children.id].service_id == service.id
    assert sessions_by_room[children.id].name == children.name
    assert sessions_by_room[children.id].min_age_years == 6
    assert sessions_by_room[children.id].max_age_years == 11

    assert inactive_room.id not in sessions_by_room


def test_create_service_rejects_active_room_without_age_range() -> None:
    room = Room(name="Sala sem configuração")

    repository = FakeCreateServiceRepository(rooms=[room])

    request = CreateServiceRequest(
        name="Culto 22/11/2026",
        starts_at=datetime(2026, 11, 22, 9, 0),
    )

    with pytest.raises(ValueError, match="age range"):
        create_service(request, repository)

    assert repository.added_services == []
    assert repository.added_sessions == []
