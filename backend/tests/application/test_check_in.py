from datetime import datetime
from uuid import UUID

import pytest

from church_city_kids.application.check_in import (
    CheckInRequest,
    ChildNotFoundError,
    SessionNotFoundError,
    check_in_child,
)
from church_city_kids.domain.attendance import Attendance
from church_city_kids.domain.errors import ChildAlreadyCheckedInError
from church_city_kids.domain.people import Child, Family
from church_city_kids.domain.scheduling import (
    Service,
    Session,
    SessionStatus,
)


class FakeCheckInRepository:
    def __init__(
        self,
        *,
        child: Child,
        family: Family,
        session: Session,
        service: Service,
    ) -> None:
        self.child = child
        self.family = family
        self.session = session
        self.service = service
        self.active_attendances: list[Attendance] = []
        self.added_attendances: list[Attendance] = []

    def get_child(self, child_id: UUID) -> Child | None:
        return self.child if self.child.id == child_id else None

    def get_family(self, family_id: UUID) -> Family | None:
        return self.family if self.family.id == family_id else None

    def get_session(self, session_id: UUID) -> Session | None:
        return self.session if self.session.id == session_id else None

    def get_service(self, service_id: UUID) -> Service | None:
        return self.service if self.service.id == service_id else None

    def get_active_attendances(
        self,
        child_id: UUID,
    ) -> list[Attendance]:
        return [
            attendance
            for attendance in self.active_attendances
            if attendance.child_id == child_id
        ]

    def add_attendance(self, attendance: Attendance) -> None:
        self.added_attendances.append(attendance)


def test_check_in_child_creates_attendance() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 4, 19, 0),
    )

    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=datetime(2021, 1, 1).date(),
    )

    session = Session(
        service_id=service.id,
        room_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Kids 3-5",
        min_age_years=3,
        max_age_years=5,
        status=SessionStatus.OPEN,
    )

    repository = FakeCheckInRepository(
        child=child,
        family=family,
        session=session,
        service=service,
    )

    occurred_at = datetime(2026, 10, 4, 18, 50)

    request = CheckInRequest(
        child_id=child.id,
        session_id=session.id,
        occurred_at=occurred_at,
    )

    result = check_in_child(request, repository)

    assert len(repository.added_attendances) == 1

    attendance = repository.added_attendances[0]

    assert attendance.id == result.attendance_id
    assert attendance.child_id == child.id
    assert attendance.session_id == session.id
    assert attendance.checked_in_at == occurred_at
    assert attendance.checked_out_at is None


def test_check_in_child_rejects_child_with_active_attendance() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 4, 19, 0),
    )

    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=datetime(2021, 1, 1).date(),
    )

    session = Session(
        service_id=service.id,
        room_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Kids 3-5",
        min_age_years=3,
        max_age_years=5,
        status=SessionStatus.OPEN,
    )

    repository = FakeCheckInRepository(
        child=child,
        family=family,
        session=session,
        service=service,
    )

    existing_attendance = Attendance(
        child_id=child.id,
        session_id=session.id,
        checked_in_at=datetime(2026, 10, 4, 18, 30),
    )
    repository.active_attendances.append(existing_attendance)

    request = CheckInRequest(
        child_id=child.id,
        session_id=session.id,
        occurred_at=datetime(2026, 10, 4, 18, 50),
    )

    with pytest.raises(ChildAlreadyCheckedInError):
        check_in_child(request, repository)

    assert repository.added_attendances == []


def test_check_in_child_rejects_unknown_child() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 4, 19, 0),
    )

    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=datetime(2021, 1, 1).date(),
    )

    session = Session(
        service_id=service.id,
        room_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Kids 3-5",
        min_age_years=3,
        max_age_years=5,
        status=SessionStatus.OPEN,
    )

    repository = FakeCheckInRepository(
        child=child,
        family=family,
        session=session,
        service=service,
    )

    request = CheckInRequest(
        child_id=UUID("00000000-0000-0000-0000-000000000099"),
        session_id=session.id,
        occurred_at=datetime(2026, 10, 4, 18, 50),
    )

    with pytest.raises(ChildNotFoundError):
        check_in_child(request, repository)

    assert repository.added_attendances == []


def test_check_in_child_rejects_unknown_session() -> None:
    service = Service(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 4, 19, 0),
    )

    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=datetime(2021, 1, 1).date(),
    )

    session = Session(
        service_id=service.id,
        room_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Kids 3-5",
        min_age_years=3,
        max_age_years=5,
        status=SessionStatus.OPEN,
    )

    repository = FakeCheckInRepository(
        child=child,
        family=family,
        session=session,
        service=service,
    )

    request = CheckInRequest(
        child_id=child.id,
        session_id=UUID("00000000-0000-0000-0000-000000000099"),
        occurred_at=datetime(2026, 10, 4, 18, 50),
    )

    with pytest.raises(SessionNotFoundError):
        check_in_child(request, repository)

    assert repository.added_attendances == []
