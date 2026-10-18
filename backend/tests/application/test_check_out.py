from datetime import date, datetime
from uuid import UUID

import pytest

from church_city_kids.application.check_out import (
    AttendanceNotFoundError,
    CheckOutRequest,
    check_out_child,
)
from church_city_kids.domain.attendance import Attendance
from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    GuardianNotAuthorizedForPickupError,
)
from church_city_kids.domain.people import ChildGuardian, Guardian
from tests.domain.factories import make_child, make_family


class FakeCheckOutRepository:
    def __init__(
        self,
        attendance: Attendance,
        *,
        child=None,
        guardian=None,
        link=None,
    ) -> None:
        self.attendance = attendance
        self.child = child
        self.guardian = guardian
        self.link = link
        self.saved_attendances: list[Attendance] = []

    def get_attendance(
        self,
        attendance_id: UUID,
    ) -> Attendance | None:
        if self.attendance.id == attendance_id:
            return self.attendance
        return None

    def get_child(self, child_id: UUID):
        if self.child is not None and self.child.id == child_id:
            return self.child
        return None

    def get_guardian(self, guardian_id: UUID):
        if self.guardian is not None and self.guardian.id == guardian_id:
            return self.guardian
        return None

    def get_child_guardian(self, child_id: UUID, guardian_id: UUID):
        if (
            self.link is not None
            and self.link.child_id == child_id
            and self.link.guardian_id == guardian_id
        ):
            return self.link
        return None

    def save_attendance(self, attendance: Attendance) -> None:
        self.saved_attendances.append(attendance)


def test_check_out_child_closes_active_attendance() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    attendance = Attendance(
        child_id=child.id,
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )

    repository = FakeCheckOutRepository(
        attendance,
        child=child,
        guardian=guardian,
        link=link,
    )

    occurred_at = datetime(2026, 10, 4, 20, 0)

    request = CheckOutRequest(
        attendance_id=attendance.id,
        guardian_id=guardian.id,
        occurred_at=occurred_at,
    )

    result = check_out_child(request, repository)

    assert result.attendance_id == attendance.id
    assert attendance.checked_out_at == occurred_at
    assert repository.saved_attendances == [attendance]


def test_check_out_child_rejects_already_checked_out_attendance() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    attendance = Attendance(
        child_id=child.id,
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
        checked_out_at=datetime(2026, 10, 4, 19, 30),
    )

    repository = FakeCheckOutRepository(
        attendance,
        child=child,
        guardian=guardian,
        link=link,
    )

    request = CheckOutRequest(
        attendance_id=attendance.id,
        guardian_id=guardian.id,
        occurred_at=datetime(2026, 10, 4, 20, 0),
    )

    with pytest.raises(AttendanceAlreadyCheckedOutError):
        check_out_child(request, repository)

    assert attendance.checked_out_at == datetime(2026, 10, 4, 19, 30)
    assert repository.saved_attendances == []


def test_check_out_child_rejects_unknown_attendance() -> None:
    attendance = Attendance(
        child_id=UUID("00000000-0000-0000-0000-000000000001"),
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )

    repository = FakeCheckOutRepository(attendance)

    request = CheckOutRequest(
        attendance_id=UUID("00000000-0000-0000-0000-000000000099"),
        occurred_at=datetime(2026, 10, 4, 20, 0),
        guardian_id=UUID("00000000-0000-0000-0000-000000000003"),
    )

    with pytest.raises(AttendanceNotFoundError):
        check_out_child(request, repository)

    assert repository.saved_attendances == []


def test_check_out_rejects_unauthorized_guardian_without_saving() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=False,
    )

    attendance = Attendance(
        child_id=child.id,
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )

    repository = FakeCheckOutRepository(
        attendance,
        child=child,
        guardian=guardian,
        link=link,
    )

    request = CheckOutRequest(
        attendance_id=attendance.id,
        guardian_id=guardian.id,
        occurred_at=datetime(2026, 10, 4, 20, 0),
    )

    with pytest.raises(GuardianNotAuthorizedForPickupError):
        check_out_child(request, repository)

    assert attendance.checked_out_at is None
    assert repository.saved_attendances == []


def test_check_out_allows_authorized_guardian() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    attendance = Attendance(
        child_id=child.id,
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )

    repository = FakeCheckOutRepository(
        attendance,
        child=child,
        guardian=guardian,
        link=link,
    )

    occurred_at = datetime(2026, 10, 4, 20, 0)

    request = CheckOutRequest(
        attendance_id=attendance.id,
        guardian_id=guardian.id,
        occurred_at=occurred_at,
    )

    result = check_out_child(request, repository)

    assert result.attendance_id == attendance.id
    assert attendance.checked_out_at == occurred_at
    assert repository.saved_attendances == [attendance]
    assert attendance.checked_out_by_guardian_id == guardian.id
