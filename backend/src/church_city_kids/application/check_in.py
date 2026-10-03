from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.attendance import Attendance, check_in
from church_city_kids.domain.people import Child, Family
from church_city_kids.domain.scheduling import Service, Session


@dataclass(frozen=True)
class CheckInRequest:
    child_id: UUID
    session_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class CheckInResult:
    attendance_id: UUID


class CheckInRepository(Protocol):
    def get_child(self, child_id: UUID) -> Child | None: ...

    def get_family(self, family_id: UUID) -> Family | None: ...

    def get_session(self, session_id: UUID) -> Session | None: ...

    def get_service(self, service_id: UUID) -> Service | None: ...

    def get_active_attendances(
        self,
        child_id: UUID,
    ) -> list[Attendance]: ...

    def add_attendance(self, attendance: Attendance) -> None: ...


def check_in_child(
    request: CheckInRequest,
    repository: CheckInRepository,
) -> CheckInResult:
    child = repository.get_child(request.child_id)
    if child is None:
        raise ChildNotFoundError()

    family = repository.get_family(child.family_id)
    assert family is not None

    session = repository.get_session(request.session_id)
    if session is None:
        raise SessionNotFoundError()

    service = repository.get_service(session.service_id)
    assert service is not None

    active_attendances = repository.get_active_attendances(child.id)

    attendance = check_in(
        child=child,
        family=family,
        session=session,
        service=service,
        active_attendances=active_attendances,
        occurred_at=request.occurred_at,
    )

    repository.add_attendance(attendance)

    return CheckInResult(attendance_id=attendance.id)


class ChildNotFoundError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass