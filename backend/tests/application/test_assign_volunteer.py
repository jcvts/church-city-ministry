from uuid import uuid4

import pytest

from church_city_kids.application.assign_volunteer import (
    AssignVolunteerRequest,
    SessionNotFoundError,
    VolunteerNotFoundError,
    assign_volunteer,
)
from church_city_kids.domain.errors import (
    VolunteerAlreadyAssignedInServiceError,
    VolunteerInactiveError,
)
from church_city_kids.domain.people import Volunteer
from church_city_kids.domain.scheduling import (
    Session,
    VolunteerAssignment,
)


class FakeAssignVolunteerRepository:
    def __init__(self) -> None:
        self.session = Session(
            service_id=uuid4(),
            room_id=uuid4(),
            name="Kids 3-5",
            min_age_years=3,
            max_age_years=5,
        )
        self.volunteer = Volunteer(full_name="Maria Oliveira")
        self.assignments: list[VolunteerAssignment] = []
        self.added_assignment: VolunteerAssignment | None = None

    def get_session(self, session_id):
        if session_id != self.session.id:
            return None
        return self.session

    def get_volunteer(self, volunteer_id):
        if volunteer_id != self.volunteer.id:
            return None
        return self.volunteer

    def get_assignments_for_service(self, service_id):
        return [
            assignment
            for assignment in self.assignments
            if assignment.service_id == service_id
        ]

    def add_assignment(self, assignment):
        self.added_assignment = assignment
        self.assignments.append(assignment)


def test_assign_volunteer_creates_assignment():
    repository = FakeAssignVolunteerRepository()

    result = assign_volunteer(
        AssignVolunteerRequest(
            session_id=repository.session.id,
            volunteer_id=repository.volunteer.id,
        ),
        repository,
    )

    assert result.assignment_id is not None
    assert repository.added_assignment is not None
    assert repository.added_assignment.session_id == repository.session.id
    assert repository.added_assignment.service_id == (repository.session.service_id)
    assert repository.added_assignment.volunteer_id == (repository.volunteer.id)


def test_assign_volunteer_preserves_role():
    repository = FakeAssignVolunteerRepository()

    result = assign_volunteer(
        AssignVolunteerRequest(
            session_id=repository.session.id,
            volunteer_id=repository.volunteer.id,
            role="Teacher",
        ),
        repository,
    )

    assert repository.added_assignment is not None
    assert repository.added_assignment.id == result.assignment_id
    assert repository.added_assignment.role == "Teacher"


def test_assign_volunteer_rejects_unknown_session():
    repository = FakeAssignVolunteerRepository()

    with pytest.raises(SessionNotFoundError):
        assign_volunteer(
            AssignVolunteerRequest(
                session_id=uuid4(),
                volunteer_id=repository.volunteer.id,
            ),
            repository,
        )

    assert repository.added_assignment is None


def test_assign_volunteer_rejects_unknown_volunteer():
    repository = FakeAssignVolunteerRepository()

    with pytest.raises(VolunteerNotFoundError):
        assign_volunteer(
            AssignVolunteerRequest(
                session_id=repository.session.id,
                volunteer_id=uuid4(),
            ),
            repository,
        )

    assert repository.added_assignment is None


def test_assign_volunteer_rejects_inactive_volunteer():
    repository = FakeAssignVolunteerRepository()
    repository.volunteer.deactivate()

    with pytest.raises(VolunteerInactiveError):
        assign_volunteer(
            AssignVolunteerRequest(
                session_id=repository.session.id,
                volunteer_id=repository.volunteer.id,
            ),
            repository,
        )

    assert repository.added_assignment is None


def test_assign_volunteer_rejects_volunteer_already_assigned_in_service():
    repository = FakeAssignVolunteerRepository()

    another_session = Session(
        service_id=repository.session.service_id,
        room_id=uuid4(),
        name="Kids 6-8",
        min_age_years=6,
        max_age_years=8,
    )

    repository.assignments.append(
        VolunteerAssignment(
            service_id=repository.session.service_id,
            session_id=another_session.id,
            volunteer_id=repository.volunteer.id,
        )
    )

    with pytest.raises(VolunteerAlreadyAssignedInServiceError):
        assign_volunteer(
            AssignVolunteerRequest(
                session_id=repository.session.id,
                volunteer_id=repository.volunteer.id,
            ),
            repository,
        )

    assert repository.added_assignment is None


def test_assign_volunteer_allows_same_volunteer_in_another_service():
    repository = FakeAssignVolunteerRepository()

    repository.assignments.append(
        VolunteerAssignment(
            service_id=uuid4(),
            session_id=uuid4(),
            volunteer_id=repository.volunteer.id,
        )
    )

    result = assign_volunteer(
        AssignVolunteerRequest(
            session_id=repository.session.id,
            volunteer_id=repository.volunteer.id,
        ),
        repository,
    )

    assert repository.added_assignment is not None
    assert repository.added_assignment.id == result.assignment_id
