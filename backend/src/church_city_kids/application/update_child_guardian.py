from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import ChildGuardian
from church_city_kids.domain.people import (
    update_child_guardian as update_child_guardian_domain,
)

_UNSET = object()


@dataclass(frozen=True)
class UpdateChildGuardianRequest:
    child_id: UUID
    guardian_id: UUID
    relationship: str | None | object = _UNSET
    authorized_pickup: bool | object = _UNSET


class UpdateChildGuardianRepository(Protocol):
    def get_child_guardian(
        self,
        child_id: UUID,
        guardian_id: UUID,
    ) -> ChildGuardian | None: ...

    def save_child_guardian(
        self,
        link: ChildGuardian,
    ) -> None: ...


class ChildGuardianNotFoundError(Exception):
    pass


def update_child_guardian(
    request: UpdateChildGuardianRequest,
    repository: UpdateChildGuardianRepository,
) -> None:
    link = repository.get_child_guardian(
        request.child_id,
        request.guardian_id,
    )

    if link is None:
        raise ChildGuardianNotFoundError()

    updates: dict[str, str | bool | None] = {}

    if isinstance(request.relationship, str) or request.relationship is None:
        updates["relationship"] = request.relationship

    if isinstance(request.authorized_pickup, bool):
        updates["authorized_pickup"] = request.authorized_pickup

    update_child_guardian_domain(link, **updates)
    repository.save_child_guardian(link)
