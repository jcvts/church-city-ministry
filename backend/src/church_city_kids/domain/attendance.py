from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    ChildAgeOutOfRangeError,
    ChildAlreadyCheckedInError,
    ChildInactiveError,
    FamilyInactiveError,
    FamilyMismatchError,
    SessionNotOpenError,
)
from church_city_kids.domain.people import Child, Family
from church_city_kids.domain.scheduling import Service, Session, SessionStatus


@dataclass
class Attendance:
    child_id: UUID
    session_id: UUID
    checked_in_at: datetime
    id: UUID = field(default_factory=uuid4)
    checked_out_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.checked_out_at is None


def check_in(
    child: Child,
    family: Family,
    session: Session,
    service: Service,
    active_attendances: list[Attendance],
    occurred_at: datetime,
) -> Attendance:
    if not child.is_active:
        raise ChildInactiveError()
    if not family.is_active:
        raise FamilyInactiveError()
    if child.family_id != family.id:
        raise FamilyMismatchError()
    if session.status is not SessionStatus.OPEN:
        raise SessionNotOpenError()
    age = child.age_on(service.starts_at.date())
    if age < session.min_age_years or age > session.max_age_years:
        raise ChildAgeOutOfRangeError()
    for attendance in active_attendances:
        if attendance.child_id == child.id and attendance.is_active:
            raise ChildAlreadyCheckedInError()
    attendance = Attendance(
        child_id=child.id,
        session_id=session.id,
        checked_in_at=occurred_at,
    )
    active_attendances.append(attendance)
    return attendance


def check_out(
    attendance: Attendance,
    occurred_at: datetime,
) -> None:
    if attendance.checked_out_at is not None:
        raise AttendanceAlreadyCheckedOutError()

    attendance.checked_out_at = occurred_at 
