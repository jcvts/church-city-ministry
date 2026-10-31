from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Child, Family, Guardian


@dataclass(frozen=True)
class FamilyChildDetail:
    id: UUID
    full_name: str
    birth_date: date
    is_active: bool


@dataclass(frozen=True)
class FamilyGuardianDetail:
    id: UUID
    full_name: str
    phone: str | None
    is_active: bool


@dataclass(frozen=True)
class FamilyDetailsResult:
    id: UUID
    is_active: bool
    children: list[FamilyChildDetail]
    guardians: list[FamilyGuardianDetail]


class GetFamilyDetailsRepository(Protocol):
    def get_family(self, family_id: UUID) -> Family | None: ...

    def get_children_for_family(
        self,
        family_id: UUID,
    ) -> list[Child]: ...

    def get_guardians_for_family(
        self,
        family_id: UUID,
    ) -> list[Guardian]: ...


def get_family_details(
    repository: GetFamilyDetailsRepository,
    *,
    family_id: UUID,
) -> FamilyDetailsResult | None:
    family = repository.get_family(family_id)

    if family is None:
        return None

    children = repository.get_children_for_family(family_id)
    guardians = repository.get_guardians_for_family(family_id)

    return FamilyDetailsResult(
        id=family.id,
        is_active=family.is_active,
        children=[
            FamilyChildDetail(
                id=child.id,
                full_name=child.full_name,
                birth_date=child.birth_date,
                is_active=child.is_active,
            )
            for child in children
        ],
        guardians=[
            FamilyGuardianDetail(
                id=guardian.id,
                full_name=guardian.full_name,
                phone=guardian.phone,
                is_active=guardian.is_active,
            )
            for guardian in guardians
        ],
    )
