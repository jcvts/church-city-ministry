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
    guardian_id: UUID | None = None
    full_name: str | None = None
    phone: str | None = None
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

    def add_guardian(self, guardian: Guardian) -> None: ...


class ChildNotFoundError(Exception):
    pass


class GuardianNotFoundError(Exception):
    pass


def add_child_guardian(
    request: AddChildGuardianRequest,
    repository: AddChildGuardianRepository,
) -> AddChildGuardianResult:
    has_guardian_id = request.guardian_id is not None
    has_full_name = bool(request.full_name and request.full_name.strip())

    if has_guardian_id == has_full_name:
        raise ValueError(
            "Provide either guardian_id or full_name, but not both"
        )

    if has_guardian_id and request.phone is not None:
        raise ValueError(
            "Phone can only be provided for a new guardian"
        )

    child = repository.get_child(request.child_id)

    if child is None:
        raise ChildNotFoundError()

    if request.guardian_id is not None:
        guardian = repository.get_guardian(request.guardian_id)

        if guardian is None:
            raise GuardianNotFoundError()
    else:
        if not request.full_name or not request.full_name.strip():
            raise ValueError("Guardian name is required")

        guardian = Guardian(
            family_id=child.family_id,
            full_name=request.full_name.strip(),
            phone=request.phone,
        )

        repository.add_guardian(guardian)

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
