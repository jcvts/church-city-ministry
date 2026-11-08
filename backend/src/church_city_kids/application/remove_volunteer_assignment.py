from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import VolunteerAssignment


class VolunteerAssignmentNotFoundError(Exception):
    pass


class RemoveVolunteerAssignmentRepository(Protocol):
    def get_by_id(self, assignment_id: UUID) -> VolunteerAssignment | None: ...

    def delete(self, assignment: VolunteerAssignment) -> None: ...


def remove_volunteer_assignment(
    assignment_id: UUID,
    repository: RemoveVolunteerAssignmentRepository,
) -> None:
    assignment = repository.get_by_id(assignment_id)

    if assignment is None:
        raise VolunteerAssignmentNotFoundError()

    repository.delete(assignment)
