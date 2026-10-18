from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    CheckOutBeforeCheckInError,
    ChildAgeOutOfRangeError,
    ChildAlreadyCheckedInError,
    ChildInactiveError,
    FamilyInactiveError,
    FamilyMismatchError,
    GuardianNotAuthorizedForPickupError,
    SessionNotOpenError,
)
from church_city_kids.domain.people import Child, ChildGuardian, Family, Guardian
from church_city_kids.domain.scheduling import Service, Session, SessionStatus


@dataclass
class Attendance:
    child_id: UUID
    session_id: UUID
    checked_in_at: datetime
    id: UUID = field(default_factory=uuid4)
    checked_out_at: datetime | None = None
    checked_out_by_guardian_id: UUID | None = None

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

    if occurred_at < attendance.checked_in_at:
        raise CheckOutBeforeCheckInError()

    attendance.checked_out_at = occurred_at


def authorize_guardian_pickup(
    child: Child,
    guardian: Guardian,
    link: ChildGuardian,
) -> None:
    if (
        not guardian.is_active
        or guardian.family_id != child.family_id
        or link.child_id != child.id
        or link.guardian_id != guardian.id
        or not link.authorized_pickup
    ):
        raise GuardianNotAuthorizedForPickupError()
