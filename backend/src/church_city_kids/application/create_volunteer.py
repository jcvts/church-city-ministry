from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from church_city_kids.domain.people import Volunteer


@dataclass(frozen=True)
class CreateVolunteerRequest:
    full_name: str


class CreateVolunteerRepository(Protocol):
    def add(self, volunteer: Volunteer) -> None: ...


def create_volunteer(
    request: CreateVolunteerRequest,
    repository: CreateVolunteerRepository,
) -> UUID:
    full_name = request.full_name.strip()

    if not full_name:
        raise ValueError("Volunteer name cannot be blank")

    volunteer = Volunteer(
        id=uuid4(),
        full_name=full_name,
        is_active=True,
    )

    repository.add(volunteer)

    return volunteer.id
