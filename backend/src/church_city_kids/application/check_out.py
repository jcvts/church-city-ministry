from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.attendance import Attendance, check_out


@dataclass(frozen=True)
class CheckOutRequest:
    attendance_id: UUID
    occurred_at: datetime


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


def check_out_child(
    request: CheckOutRequest,
    repository: CheckOutRepository,
) -> CheckOutResult:
    attendance = repository.get_attendance(request.attendance_id)

    if attendance is None:
        raise AttendanceNotFoundError()

    check_out(
        attendance=attendance,
        occurred_at=request.occurred_at,
    )

    repository.save_attendance(attendance)

    return CheckOutResult(attendance_id=attendance.id)


class AttendanceNotFoundError(Exception):
    pass
