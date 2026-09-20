from datetime import date, datetime

import pytest

from church_city_kids.domain.attendance import Attendance, check_in, check_out
from church_city_kids.domain.errors import (
    AttendanceAlreadyHasPagerError,
    AttendanceNotActiveError,
    PagerAlreadyAssignedError,
    PagerInactiveError,
)
from church_city_kids.domain.pager import Pager, PagerAssignment, assign_pager
from tests.domain.factories import (
    make_child,
    make_family,
    make_open_session,
    make_room,
    make_service,
)


def _checked_in() -> Attendance:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = make_open_session(service, make_room())
    attendance = check_in(
        child, family, session, service, [], datetime(2026, 9, 20, 9, 50)
    )
    return attendance


def test_assign_pager_to_active_attendance() -> None:
    attendance = _checked_in()
    pager = Pager(code="12")
    assignment = assign_pager(attendance, pager, [], datetime(2026, 9, 20, 9, 51))
    assert assignment.pager_id == pager.id
    assert assignment.attendance_id == attendance.id
    assert assignment.is_active


def test_same_pager_cannot_be_assigned_twice() -> None:
    first = _checked_in()
    second = _checked_in()
    pager = Pager(code="12")
    assignments: list[PagerAssignment] = []
    assign_pager(first, pager, assignments, datetime(2026, 9, 20, 9, 51))
    with pytest.raises(PagerAlreadyAssignedError):
        assign_pager(second, pager, assignments, datetime(2026, 9, 20, 9, 52))


def test_attendance_cannot_have_two_active_pagers() -> None:
    attendance = _checked_in()
    assignments: list[PagerAssignment] = []
    assign_pager(
        attendance, Pager(code="12"), assignments, datetime(2026, 9, 20, 9, 51)
    )
    with pytest.raises(AttendanceAlreadyHasPagerError):
        assign_pager(
            attendance, Pager(code="13"), assignments, datetime(2026, 9, 20, 9, 52)
        )


def test_cannot_assign_pager_to_checked_out_attendance() -> None:
    attendance = _checked_in()
    check_out(attendance, datetime(2026, 9, 20, 11, 0))
    with pytest.raises(AttendanceNotActiveError):
        assign_pager(attendance, Pager(code="12"), [], datetime(2026, 9, 20, 11, 1))


def test_releasing_pager_assignment_keeps_history() -> None:
    attendance = _checked_in()
    pager = Pager(code="12")
    assignments: list[PagerAssignment] = []
    assignment = assign_pager(
        attendance, pager, assignments, datetime(2026, 9, 20, 9, 51)
    )
    released_at = datetime(2026, 9, 20, 11, 0)

    assignment.release(released_at)

    assert assignment.released_at == released_at
    assert assignment.is_active is False
    assert assignment in assignments


def test_inactive_pager_cannot_be_assigned() -> None:
    attendance = _checked_in()
    pager = Pager(code="12")
    pager.deactivate()

    with pytest.raises(PagerInactiveError):
        assign_pager(
            attendance,
            pager,
            [],
            datetime(2026, 9, 20, 9, 51),
        )
