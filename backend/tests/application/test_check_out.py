from datetime import datetime
from uuid import UUID

import pytest

from church_city_kids.application.check_out import (
    AttendanceNotFoundError,
    CheckOutRequest,
    check_out_child,
)
from church_city_kids.domain.attendance import Attendance
from church_city_kids.domain.errors import AttendanceAlreadyCheckedOutError


class FakeCheckOutRepository:
    def __init__(self, attendance: Attendance) -> None:
        self.attendance = attendance
        self.saved_attendances: list[Attendance] = []

    def get_attendance(
        self,
        attendance_id: UUID,
    ) -> Attendance | None:
        if self.attendance.id == attendance_id:
            return self.attendance
        return None

    def save_attendance(self, attendance: Attendance) -> None:
        self.saved_attendances.append(attendance)


def test_check_out_child_closes_active_attendance() -> None:
    attendance = Attendance(
        child_id=UUID("00000000-0000-0000-0000-000000000001"),
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )

    repository = FakeCheckOutRepository(attendance)

    occurred_at = datetime(2026, 10, 4, 20, 0)

    request = CheckOutRequest(
        attendance_id=attendance.id,
        occurred_at=occurred_at,
    )

    result = check_out_child(request, repository)

    assert result.attendance_id == attendance.id
    assert attendance.checked_out_at == occurred_at
    assert repository.saved_attendances == [attendance]


def test_check_out_child_rejects_already_checked_out_attendance() -> None:
    attendance = Attendance(
        child_id=UUID("00000000-0000-0000-0000-000000000001"),
        session_id=UUID("00000000-0000-0000-0000-000000000002"),
        checked_in_at=datetime(2026, 10, 4, 18, 30),
        checked_out_at=datetime(2026, 10, 4, 19, 30),
    )

    repository = FakeCheckOutRepository(attendance)

    request = CheckOutRequest(
        attendance_id=attendance.id,
        occurred_at=datetime(2026, 10, 4, 20, 0),
    )

    with pytest.raises(AttendanceAlreadyCheckedOutError):
        check_out_child(request, repository)

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
    )

    with pytest.raises(AttendanceNotFoundError):
        check_out_child(request, repository)

    assert repository.saved_attendances == []
