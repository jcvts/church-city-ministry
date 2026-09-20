from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from church_city_kids.domain.errors import (
    InvalidAgeRangeError,
    InvalidServiceScheduleError,
    RoomAlreadyAssignedInServiceError,
    VolunteerAlreadyAssignedInServiceError,
)
from church_city_kids.domain.people import Volunteer

RECOMMENDED_VOLUNTEERS_PER_SESSION = 2


class SessionStatus(Enum):
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Service:
    name: str
    starts_at: datetime
    id: UUID = field(default_factory=uuid4)
    ends_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise InvalidServiceScheduleError()


@dataclass
class Room:
    name: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class Session:
    service_id: UUID
    room_id: UUID
    name: str
    min_age_years: int
    max_age_years: int
    id: UUID = field(default_factory=uuid4)
    status: SessionStatus = SessionStatus.SCHEDULED

    def __post_init__(self) -> None:
        if self.min_age_years < 0 or self.max_age_years < 0:
            raise InvalidAgeRangeError()
        if self.min_age_years > self.max_age_years:
            raise InvalidAgeRangeError()


@dataclass
class VolunteerAssignment:
    session_id: UUID
    volunteer_id: UUID
    id: UUID = field(default_factory=uuid4)
    role: str | None = None


def create_session(
    service: Service,
    room: Room,
    name: str,
    min_age_years: int,
    max_age_years: int,
    existing_sessions: list[Session],
    *,
    status: SessionStatus = SessionStatus.SCHEDULED,
) -> Session:
    for session in existing_sessions:
        if session.service_id == service.id and session.room_id == room.id:
            raise RoomAlreadyAssignedInServiceError()
    session = Session(
        service_id=service.id,
        room_id=room.id,
        name=name,
        min_age_years=min_age_years,
        max_age_years=max_age_years,
        status=status,
    )
    existing_sessions.append(session)
    return session


def assign_volunteer(
    session: Session,
    volunteer: Volunteer,
    assignments_in_service: list[VolunteerAssignment],
    *,
    role: str | None = None,
) -> VolunteerAssignment:
    for assignment in assignments_in_service:
        if assignment.volunteer_id == volunteer.id:
            raise VolunteerAlreadyAssignedInServiceError()
    assignment = VolunteerAssignment(
        session_id=session.id,
        volunteer_id=volunteer.id,
        role=role,
    )
    assignments_in_service.append(assignment)
    return assignment
