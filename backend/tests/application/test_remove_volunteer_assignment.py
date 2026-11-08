from uuid import uuid4

import pytest

from church_city_kids.application.remove_volunteer_assignment import (
    VolunteerAssignmentNotFoundError,
    remove_volunteer_assignment,
)
from church_city_kids.domain.scheduling import VolunteerAssignment


class FakeRemoveVolunteerAssignmentRepository:
    def __init__(self) -> None:
        self.assignment = VolunteerAssignment(
            service_id=uuid4(),
            session_id=uuid4(),
            volunteer_id=uuid4(),
        )
        self.assignments = {self.assignment.id: self.assignment}

    def get_by_id(self, assignment_id):
        return self.assignments.get(assignment_id)

    def delete(self, assignment):
        del self.assignments[assignment.id]


def test_remove_volunteer_assignment_deletes_existing_assignment():
    repository = FakeRemoveVolunteerAssignmentRepository()
    assignment_id = repository.assignment.id

    remove_volunteer_assignment(assignment_id, repository)

    assert assignment_id not in repository.assignments


def test_remove_volunteer_assignment_rejects_unknown_assignment():
    repository = FakeRemoveVolunteerAssignmentRepository()
    existing_assignment_id = repository.assignment.id

    with pytest.raises(VolunteerAssignmentNotFoundError):
        remove_volunteer_assignment(uuid4(), repository)

    assert existing_assignment_id in repository.assignments
