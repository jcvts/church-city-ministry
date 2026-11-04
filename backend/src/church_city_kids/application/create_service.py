from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import (
    Room,
    Service,
    Session,
)
from church_city_kids.domain.scheduling import (
    create_session as create_domain_session,
)


@dataclass(frozen=True)
class CreateServiceRequest:
    name: str
    starts_at: datetime
    ends_at: datetime | None = None


@dataclass(frozen=True)
class CreateServiceResult:
    service_id: UUID


class RoomAgeRangeNotConfiguredError(ValueError):
    pass


class CreateServiceRepository(Protocol):
    def get_active_rooms(self) -> list[Room]: ...

    def add_service(self, service: Service) -> None: ...

    def add_session(self, session: Session) -> None: ...


def create_service(
    request: CreateServiceRequest,
    repository: CreateServiceRepository,
) -> CreateServiceResult:
    rooms = repository.get_active_rooms()

    # Validate all rooms before persisting anything.
    for room in rooms:
        if room.min_age_years is None or room.max_age_years is None:
            raise RoomAgeRangeNotConfiguredError(
                f"Room '{room.name}' has no age range configured"
            )

    service = Service(
        name=request.name,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
    )

    existing_sessions: list[Session] = []
    
    sessions: list[Session] = []

    for room in rooms:
        assert room.min_age_years is not None
        assert room.max_age_years is not None

        session = create_domain_session(
            service=service,
            room=room,
            name=room.name,
            min_age_years=room.min_age_years,
            max_age_years=room.max_age_years,
            existing_sessions=existing_sessions,
        )

        sessions.append(session)


    repository.add_service(service)

    for session in sessions:
        repository.add_session(session)

    return CreateServiceResult(service_id=service.id)
