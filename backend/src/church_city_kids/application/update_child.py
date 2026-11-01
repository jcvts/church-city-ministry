from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Child

_UNSET = object()


@dataclass(frozen=True)
class UpdateChildRequest:
    child_id: UUID
    full_name: str | object = _UNSET
    birth_date: date | object = _UNSET


class UpdateChildRepository(Protocol):
    def get_child(self, child_id: UUID) -> Child | None: ...

    def save_child(self, child: Child) -> None: ...


class ChildNotFoundError(Exception):
    pass


def update_child(
    request: UpdateChildRequest,
    repository: UpdateChildRepository,
) -> None:
    if request.full_name is _UNSET and request.birth_date is _UNSET:
        raise ValueError("At least one field must be provided")

    # Validate all supplied fields before changing the entity.
    if request.full_name is not _UNSET:
        if not isinstance(request.full_name, str):
            raise ValueError("Invalid child name")

        if not request.full_name.strip():
            raise ValueError("Child name cannot be blank")

    if request.birth_date is not _UNSET:
        if not isinstance(request.birth_date, date):
            raise ValueError("Invalid birth date")

    child = repository.get_child(request.child_id)

    if child is None:
        raise ChildNotFoundError()

    # Apply changes only after all validations succeed.
    if isinstance(request.full_name, str):
        child.full_name = request.full_name.strip()

    if isinstance(request.birth_date, date):
        child.birth_date = request.birth_date

    repository.save_child(child)
