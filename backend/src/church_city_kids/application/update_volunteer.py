from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Volunteer

_UNSET = object()


@dataclass(frozen=True)
class UpdateVolunteerRequest:
    volunteer_id: UUID
    full_name: str | object = _UNSET


class UpdateVolunteerRepository(Protocol):
    def get_by_id(self, volunteer_id: UUID) -> Volunteer | None: ...

    def update(self, volunteer: Volunteer) -> None: ...


class VolunteerNotFoundError(Exception):
    pass


def update_volunteer(
    request: UpdateVolunteerRequest,
    repository: UpdateVolunteerRepository,
) -> None:
    if request.full_name is _UNSET:
        raise ValueError("At least one field must be provided")

    if not isinstance(request.full_name, str):
        raise ValueError("Invalid volunteer name")

    if not request.full_name.strip():
        raise ValueError("Volunteer name cannot be blank")

    volunteer = repository.get_by_id(request.volunteer_id)

    if volunteer is None:
        raise VolunteerNotFoundError()

    volunteer.full_name = request.full_name.strip()

    repository.update(volunteer)
