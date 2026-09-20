from datetime import date, datetime

import pytest

from church_city_kids.domain.attendance import Attendance, check_in, check_out
from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    ChildAgeOutOfRangeError,
    ChildAlreadyCheckedInError,
    ChildInactiveError,
    FamilyInactiveError,
    SessionNotOpenError,
)
from church_city_kids.domain.scheduling import SessionStatus, create_session
from tests.domain.factories import (
    make_child,
    make_family,
    make_open_session,
    make_room,
    make_service,
)


def _check_in_age(
    *,
    birth_date: date,
    min_age: int,
    max_age: int,
    service_date: datetime,
) -> Attendance:
    family = make_family()
    child = make_child(family, birth_date=birth_date)
    service = make_service(starts_at=service_date)
    session = make_open_session(
        service, make_room(), min_age_years=min_age, max_age_years=max_age
    )
    return check_in(
        child, family, session, service, [], occurred_at=service_date
    )


def test_age_five_fits_three_to_five_not_six_to_eleven() -> None:
    service_date = datetime(2026, 9, 20, 10, 0)
    birth_date = date(2021, 9, 20)
    attendance = _check_in_age(
        birth_date=birth_date, min_age=3, max_age=5, service_date=service_date
    )
    assert attendance.checked_out_at is None

    with pytest.raises(ChildAgeOutOfRangeError) as exc_info:
        _check_in_age(
            birth_date=birth_date, min_age=6, max_age=11, service_date=service_date
        )
    assert "Joao Child" not in str(exc_info.value)
    assert "2021" not in str(exc_info.value)


def test_age_two_and_twelve_are_rejected() -> None:
    service_date = datetime(2026, 9, 20, 10, 0)
    with pytest.raises(ChildAgeOutOfRangeError):
        _check_in_age(
            birth_date=date(2024, 9, 20),
            min_age=3,
            max_age=5,
            service_date=service_date,
        )
    with pytest.raises(ChildAgeOutOfRangeError):
        _check_in_age(
            birth_date=date(2014, 9, 20),
            min_age=6,
            max_age=11,
            service_date=service_date,
        )


def test_birthday_on_service_date_counts_as_new_age() -> None:
    service_date = datetime(2026, 9, 20, 10, 0)
    attendance = _check_in_age(
        birth_date=date(2020, 9, 20),
        min_age=6,
        max_age=11,
        service_date=service_date,
    )
    assert attendance.is_active


def test_check_in_creates_active_attendance_for_session() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = make_open_session(service, make_room())
    occurred_at = datetime(2026, 9, 20, 9, 55)

    attendance = check_in(child, family, session, service, [], occurred_at)

    assert attendance.child_id == child.id
    assert attendance.session_id == session.id
    assert attendance.checked_in_at == occurred_at
    assert attendance.is_active


def test_second_active_check_in_is_rejected() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    first = make_open_session(service, make_room("A"))
    second = make_open_session(
        service,
        make_room("B"),
        min_age_years=3,
        max_age_years=5,
        name="Other",
        existing=[first],
    )
    active: list[Attendance] = []
    check_in(child, family, first, service, active, datetime(2026, 9, 20, 9, 50))

    with pytest.raises(ChildAlreadyCheckedInError):
        check_in(child, family, second, service, active, datetime(2026, 9, 20, 9, 51))


def test_check_in_after_checkout_preserves_history() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = make_open_session(service, make_room())
    first = check_in(
        child, family, session, service, [], datetime(2026, 9, 20, 9, 50)
    )
    check_out(first, datetime(2026, 9, 20, 11, 0))

    second = check_in(
        child, family, session, service, [first], datetime(2026, 9, 20, 11, 5)
    )

    assert first.checked_out_at is not None
    assert second.is_active
    assert first.id != second.id


def test_inactive_child_or_family_cannot_check_in() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = make_open_session(service, make_room())
    occurred_at = datetime(2026, 9, 20, 9, 50)

    child.deactivate()
    with pytest.raises(ChildInactiveError):
        check_in(child, family, session, service, [], occurred_at)

    child.is_active = True
    family.deactivate()
    with pytest.raises(FamilyInactiveError):
        check_in(child, family, session, service, [], occurred_at)


@pytest.mark.parametrize(
    "status",
    [SessionStatus.SCHEDULED, SessionStatus.CLOSED, SessionStatus.CANCELLED],
)
def test_check_in_rejected_when_session_not_open(status: SessionStatus) -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = create_session(
        service, make_room(), "Kids 3-5", 3, 5, [], status=status
    )
    with pytest.raises(SessionNotOpenError):
        check_in(child, family, session, service, [], datetime(2026, 9, 20, 9, 50))


def test_checkout_of_already_checked_out_attendance_fails() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    service = make_service()
    session = make_open_session(service, make_room())
    attendance = check_in(
        child, family, session, service, [], datetime(2026, 9, 20, 9, 50)
    )
    check_out(attendance, datetime(2026, 9, 20, 11, 0))
    with pytest.raises(AttendanceAlreadyCheckedOutError):
        check_out(attendance, datetime(2026, 9, 20, 11, 5))
