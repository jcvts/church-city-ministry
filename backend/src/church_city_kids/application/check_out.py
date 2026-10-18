from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.attendance import (
    Attendance,
    authorize_guardian_pickup,
    check_out,
)
from church_city_kids.domain.errors import GuardianNotAuthorizedForPickupError
from church_city_kids.domain.people import Child, ChildGuardian, Guardian


@dataclass(frozen=True)
class CheckOutRequest:
    attendance_id: UUID
    occurred_at: datetime
    guardian_id: UUID


@dataclass(frozen=True)
class CheckOutResult:
    attendance_id: UUID


class CheckOutRepository(Protocol):
    def get_attendance(
        self,
        attendance_id: UUID,
    ) -> Attendance | None: ...

    def save_attendance(
        self,
        attendance: Attendance,
    ) -> None: ...

    def get_child(self, child_id: UUID) -> Child | None: ...

    def get_guardian(self, guardian_id: UUID) -> Guardian | None: ...

    def get_child_guardian(
        self,
        child_id: UUID,
        guardian_id: UUID,
    ) -> ChildGuardian | None: ...


def check_out_child(
    request: CheckOutRequest,
    repository: CheckOutRepository,
) -> CheckOutResult:
    attendance = repository.get_attendance(request.attendance_id)

    if attendance is None:
        raise AttendanceNotFoundError()

    child = repository.get_child(attendance.child_id)
    guardian = repository.get_guardian(request.guardian_id)
    link = repository.get_child_guardian(
        attendance.child_id,
        request.guardian_id,
    )

    if child is None or guardian is None or link is None:
        raise GuardianNotAuthorizedForPickupError()

    authorize_guardian_pickup(
        child=child,
        guardian=guardian,
        link=link,
    )

    check_out(
        attendance=attendance,
        occurred_at=request.occurred_at,
    )

    attendance.checked_out_by_guardian_id = guardian.id

    repository.save_attendance(attendance)

    return CheckOutResult(attendance_id=attendance.id)


class AttendanceNotFoundError(Exception):
    pass
