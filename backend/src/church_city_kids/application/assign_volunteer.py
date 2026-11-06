from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Volunteer
from church_city_kids.domain.scheduling import (
    Session,
    VolunteerAssignment,
)
from church_city_kids.domain.scheduling import (
    assign_volunteer as assign_domain_volunteer,
)


@dataclass(frozen=True)
class AssignVolunteerRequest:
    session_id: UUID
    volunteer_id: UUID
    role: str | None = None


@dataclass(frozen=True)
class AssignVolunteerResult:
    assignment_id: UUID


class SessionNotFoundError(Exception):
    pass


class VolunteerNotFoundError(Exception):
    pass


class AssignVolunteerRepository(Protocol):
    def get_session(self, session_id: UUID) -> Session | None: ...

    def get_volunteer(self, volunteer_id: UUID) -> Volunteer | None: ...

    def get_assignments_for_service(
        self,
        service_id: UUID,
    ) -> list[VolunteerAssignment]: ...

    def add_assignment(
        self,
        assignment: VolunteerAssignment,
    ) -> None: ...


def assign_volunteer(
    request: AssignVolunteerRequest,
    repository: AssignVolunteerRepository,
) -> AssignVolunteerResult:
    session = repository.get_session(request.session_id)

    if session is None:
        raise SessionNotFoundError()

    volunteer = repository.get_volunteer(request.volunteer_id)

    if volunteer is None:
        raise VolunteerNotFoundError()

    existing_assignments = repository.get_assignments_for_service(session.service_id)

    assignment = assign_domain_volunteer(
        session=session,
        volunteer=volunteer,
        assignments_in_service=existing_assignments,
        role=request.role,
    )

    repository.add_assignment(assignment)

    return AssignVolunteerResult(
        assignment_id=assignment.id,
    )
