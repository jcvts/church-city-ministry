from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Family


@dataclass(frozen=True)
class UpdateFamilyRequest:
    family_id: UUID
    is_active: bool


class UpdateFamilyRepository(Protocol):
    def get_family(self, family_id: UUID) -> Family | None: ...

    def save_family(self, family: Family) -> None: ...


class FamilyNotFoundError(Exception):
    pass


def update_family(
    request: UpdateFamilyRequest,
    repository: UpdateFamilyRepository,
) -> None:
    if not isinstance(request.is_active, bool):
        raise ValueError("Invalid family status")

    family = repository.get_family(request.family_id)

    if family is None:
        raise FamilyNotFoundError()

    family.is_active = request.is_active

    repository.save_family(family)
