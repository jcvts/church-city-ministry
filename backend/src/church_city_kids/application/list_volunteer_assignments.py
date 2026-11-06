from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class VolunteerAssignmentItem:
    assignment_id: UUID
    service_id: UUID
    session_id: UUID
    volunteer_id: UUID
    volunteer_name: str
    role: str | None


class ListVolunteerAssignmentsRepository(Protocol):
    def service_exists(self, service_id: UUID) -> bool: ...

    def list_for_service(
        self,
        service_id: UUID,
    ) -> list[VolunteerAssignmentItem]: ...


class ServiceNotFoundError(Exception):
    pass


def list_volunteer_assignments(
    service_id: UUID,
    repository: ListVolunteerAssignmentsRepository,
) -> list[VolunteerAssignmentItem]:
    if not repository.service_exists(service_id):
        raise ServiceNotFoundError()

    return repository.list_for_service(service_id)
