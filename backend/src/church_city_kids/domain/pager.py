from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.domain.attendance import Attendance
from church_city_kids.domain.errors import (
    AttendanceAlreadyHasPagerError,
    AttendanceNotActiveError,
    PagerAlreadyAssignedError,
    PagerInactiveError,
)


@dataclass
class Pager:
    code: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class PagerAssignment:
    pager_id: UUID
    attendance_id: UUID
    assigned_at: datetime
    id: UUID = field(default_factory=uuid4)
    released_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.released_at is None

    def release(self, occurred_at: datetime) -> None:
        if self.released_at is None:
            self.released_at = occurred_at


def assign_pager(
    attendance: Attendance,
    pager: Pager,
    active_assignments: list[PagerAssignment],
    occurred_at: datetime,
) -> PagerAssignment:
    if not attendance.is_active:
        raise AttendanceNotActiveError()
    if not pager.is_active:
        raise PagerInactiveError()
    for assignment in active_assignments:
        if not assignment.is_active:
            continue
        if assignment.pager_id == pager.id:
            raise PagerAlreadyAssignedError()
        if assignment.attendance_id == attendance.id:
            raise AttendanceAlreadyHasPagerError()
    assignment = PagerAssignment(
        pager_id=pager.id,
        attendance_id=attendance.id,
        assigned_at=occurred_at,
    )
    active_assignments.append(assignment)
    return assignment
