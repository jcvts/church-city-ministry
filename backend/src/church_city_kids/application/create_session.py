from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import (
    Room,
    Service,
    Session,
)
from church_city_kids.domain.scheduling import create_session as create_domain_session


@dataclass(frozen=True)
class CreateSessionRequest:
    service_id: UUID
    room_id: UUID
    name: str
    min_age_years: int
    max_age_years: int


@dataclass(frozen=True)
class CreateSessionResult:
    session_id: UUID


class ServiceNotFoundError(Exception):
    pass


class RoomNotFoundError(Exception):
    pass


class CreateSessionRepository(Protocol):
    def get_service(self, service_id: UUID) -> Service | None: ...

    def get_room(self, room_id: UUID) -> Room | None: ...

    def get_sessions_for_service(self, service_id: UUID) -> list[Session]: ...

    def add_session(self, session: Session) -> None: ...


def create_session(
    request: CreateSessionRequest,
    repository: CreateSessionRepository,
) -> CreateSessionResult:
    service = repository.get_service(request.service_id)

    if service is None:
        raise ServiceNotFoundError()

    room = repository.get_room(request.room_id)

    if room is None:
        raise RoomNotFoundError()

    existing_sessions = repository.get_sessions_for_service(service.id)

    session = create_domain_session(
        service=service,
        room=room,
        name=request.name,
        min_age_years=request.min_age_years,
        max_age_years=request.max_age_years,
        existing_sessions=existing_sessions,
    )

    repository.add_session(session)

    return CreateSessionResult(session_id=session.id)
