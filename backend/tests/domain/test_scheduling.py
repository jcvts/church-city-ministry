from datetime import datetime

import pytest

from church_city_kids.domain.errors import (
    InvalidAgeRangeError,
    InvalidServiceScheduleError,
    RoomAlreadyAssignedInServiceError,
    VolunteerAlreadyAssignedInServiceError,
)
from church_city_kids.domain.scheduling import (
    Session,
    SessionStatus,
    VolunteerAssignment,
    assign_volunteer,
    create_session,
)
from tests.domain.factories import (
    make_room,
    make_service,
    make_volunteer,
)


def test_service_allows_missing_ends_at() -> None:
    service = make_service(ends_at=None)
    assert service.ends_at is None


def test_service_rejects_ends_at_not_after_starts_at() -> None:
    starts_at = datetime(2026, 9, 20, 10, 0)
    with pytest.raises(InvalidServiceScheduleError):
        make_service(starts_at=starts_at, ends_at=starts_at)
    with pytest.raises(InvalidServiceScheduleError):
        make_service(starts_at=starts_at, ends_at=datetime(2026, 9, 20, 9, 0))


def test_same_room_cannot_be_used_twice_in_the_same_service() -> None:
    service = make_service()
    room = make_room()
    existing: list[Session] = []
    create_session(service, room, "Kids 3-5", 3, 5, existing, status=SessionStatus.OPEN)

    with pytest.raises(RoomAlreadyAssignedInServiceError):
        create_session(
            service, room, "Kids 6-11", 6, 11, existing, status=SessionStatus.OPEN
        )


def test_same_room_can_be_used_in_different_services() -> None:
    room = make_room()
    morning = make_service(starts_at=datetime(2026, 9, 20, 10, 0))
    evening = make_service(starts_at=datetime(2026, 9, 20, 18, 0))
    sessions: list[Session] = []
    first = create_session(morning, room, "Kids 3-5", 3, 5, sessions)
    second = create_session(evening, room, "Kids 3-5", 3, 5, sessions)
    assert first.room_id == second.room_id == room.id
    assert first.service_id != second.service_id


def test_same_volunteer_cannot_be_assigned_to_two_sessions_in_the_same_service(
) -> None:
    service = make_service()
    room_a = make_room("A")
    room_b = make_room("B")
    sessions: list[Session] = []
    first = create_session(service, room_a, "Kids 3-5", 3, 5, sessions)
    second = create_session(service, room_b, "Kids 6-11", 6, 11, sessions)
    volunteer = make_volunteer()
    assignments: list[VolunteerAssignment] = []
    assign_volunteer(first, volunteer, assignments)

    with pytest.raises(VolunteerAlreadyAssignedInServiceError):
        assign_volunteer(second, volunteer, assignments)


def test_same_volunteer_can_be_assigned_in_different_services() -> None:
    morning = make_service(starts_at=datetime(2026, 9, 20, 10, 0))
    evening = make_service(starts_at=datetime(2026, 9, 20, 18, 0))
    room = make_room()
    morning_session = create_session(morning, room, "Kids 3-5", 3, 5, [])
    evening_session = create_session(evening, make_room("B"), "Kids 3-5", 3, 5, [])
    volunteer = make_volunteer()

    first = assign_volunteer(morning_session, volunteer, [])
    second = assign_volunteer(evening_session, volunteer, [])

    assert first.volunteer_id == second.volunteer_id == volunteer.id
    assert first.session_id != second.session_id


def test_duplicate_volunteer_on_the_same_session_is_rejected() -> None:
    service = make_service()
    session = create_session(service, make_room(), "Kids 3-5", 3, 5, [])
    volunteer = make_volunteer()
    assignments: list[VolunteerAssignment] = []
    assign_volunteer(session, volunteer, assignments)

    with pytest.raises(VolunteerAlreadyAssignedInServiceError):
        assign_volunteer(session, volunteer, assignments)


def test_one_or_three_volunteers_can_be_assigned_to_a_session() -> None:
    service = make_service()
    session = create_session(service, make_room(), "Kids 3-5", 3, 5, [])
    assignments: list[VolunteerAssignment] = []
    assign_volunteer(session, make_volunteer("One"), assignments)
    assert len(assignments) == 1

    session_b = create_session(service, make_room("B"), "Kids 6-11", 6, 11, [])
    three: list[VolunteerAssignment] = []
    assign_volunteer(session_b, make_volunteer("A"), three)
    assign_volunteer(session_b, make_volunteer("B"), three)
    assign_volunteer(session_b, make_volunteer("C"), three)
    assert len(three) == 3


def test_volunteer_assignment_does_not_require_role() -> None:
    service = make_service()
    session = create_session(service, make_room(), "Kids 3-5", 3, 5, [])
    assignment = assign_volunteer(session, make_volunteer(), [])
    assert assignment.role is None


def test_session_rejects_invalid_age_range() -> None:
    service = make_service()
    room = make_room()
    with pytest.raises(InvalidAgeRangeError):
        create_session(service, room, "Invalid", 6, 3, [])
    with pytest.raises(InvalidAgeRangeError):
        create_session(service, room, "Invalid", -1, 5, [])
