from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Child, ChildGuardian, Guardian


@dataclass(frozen=True)
class GuardianDetail:
    id: UUID
    full_name: str
    phone: str | None
    relationship: str | None
    authorized_pickup: bool
    is_active: bool


@dataclass(frozen=True)
class ChildDetailsResult:
    id: UUID
    family_id: UUID
    full_name: str
    birth_date: date
    guardians: list[GuardianDetail]


class GetChildDetailsRepository(Protocol):
    def get_child(self, child_id: UUID) -> Child | None: ...

    def get_guardians_for_child(
        self,
        child_id: UUID,
    ) -> list[tuple[Guardian, ChildGuardian]]: ...


def get_child_details(
    repository: GetChildDetailsRepository,
    *,
    child_id: UUID,
) -> ChildDetailsResult | None:
    child = repository.get_child(child_id)

    if child is None:
        return None

    guardians = repository.get_guardians_for_child(child_id)

    return ChildDetailsResult(
        id=child.id,
        family_id=child.family_id,
        full_name=child.full_name,
        birth_date=child.birth_date,
        guardians=[
            GuardianDetail(
                id=guardian.id,
                full_name=guardian.full_name,
                phone=guardian.phone,
                relationship=link.relationship,
                authorized_pickup=link.authorized_pickup,
                is_active=guardian.is_active,
            )
            for guardian, link in guardians
        ],
    )
