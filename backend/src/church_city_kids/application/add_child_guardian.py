from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Guardian,
    link_child_guardian,
)


@dataclass(frozen=True)
class AddChildGuardianRequest:
    child_id: UUID
    guardian_id: UUID
    relationship: str | None = None
    authorized_pickup: bool = False


@dataclass(frozen=True)
class AddChildGuardianResult:
    link_id: UUID


class AddChildGuardianRepository(Protocol):
    def get_child(self, child_id: UUID) -> Child | None: ...

    def get_guardian(self, guardian_id: UUID) -> Guardian | None: ...

    def get_child_guardians(self, child_id: UUID) -> list[ChildGuardian]: ...

    def add_child_guardian(self, link: ChildGuardian) -> None: ...


class ChildNotFoundError(Exception):
    pass


class GuardianNotFoundError(Exception):
    pass


def add_child_guardian(
    request: AddChildGuardianRequest,
    repository: AddChildGuardianRepository,
) -> AddChildGuardianResult:
    child = repository.get_child(request.child_id)

    if child is None:
        raise ChildNotFoundError()

    guardian = repository.get_guardian(request.guardian_id)

    if guardian is None:
        raise GuardianNotFoundError()

    existing_links = repository.get_child_guardians(child.id)

    link = link_child_guardian(
        child,
        guardian,
        existing_links,
        relationship=request.relationship,
        authorized_pickup=request.authorized_pickup,
    )

    repository.add_child_guardian(link)

    return AddChildGuardianResult(link_id=link.id)
