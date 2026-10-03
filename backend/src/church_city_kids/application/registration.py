from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
    link_child_guardian,
)


@dataclass(frozen=True)
class RegisterChildRequest:
    child_name: str
    birth_date: date
    guardian_name: str
    guardian_phone: str | None = None
    relationship: str | None = None


@dataclass(frozen=True)
class RegisterChildResult:
    family_id: UUID
    child_id: UUID
    guardian_id: UUID


class RegistrationRepository(Protocol):
    def add_family(self, family: Family) -> None: ...

    def add_guardian(self, guardian: Guardian) -> None: ...

    def add_child(self, child: Child) -> None: ...

    def add_child_guardian(self, link: ChildGuardian) -> None: ...


def register_child(
    request: RegisterChildRequest,
    repository: RegistrationRepository,
) -> RegisterChildResult:
    family = Family()

    guardian = Guardian(
        family_id=family.id,
        full_name=request.guardian_name,
        phone=request.guardian_phone,
    )

    child = Child(
        family_id=family.id,
        full_name=request.child_name,
        birth_date=request.birth_date,
    )

    link = link_child_guardian(
        child,
        guardian,
        [],
        relationship=request.relationship,
    )

    repository.add_family(family)
    repository.add_guardian(guardian)
    repository.add_child(child)
    repository.add_child_guardian(link)

    return RegisterChildResult(
        family_id=family.id,
        child_id=child.id,
        guardian_id=guardian.id,
    )