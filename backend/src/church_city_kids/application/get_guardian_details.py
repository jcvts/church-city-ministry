from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Child, ChildGuardian, Guardian


@dataclass(frozen=True)
class GuardianChildDetail:
    id: UUID
    family_id: UUID
    full_name: str
    birth_date: date
    is_active: bool
    relationship: str | None
    authorized_pickup: bool


@dataclass(frozen=True)
class GuardianDetailsResult:
    id: UUID
    family_id: UUID
    full_name: str
    phone: str | None
    is_active: bool
    children: list[GuardianChildDetail]


class GetGuardianDetailsRepository(Protocol):
    def get_guardian(self, guardian_id: UUID) -> Guardian | None: ...

    def get_children_for_guardian(
        self,
        guardian_id: UUID,
    ) -> list[tuple[Child, ChildGuardian]]: ...


def get_guardian_details(
    repository: GetGuardianDetailsRepository,
    *,
    guardian_id: UUID,
) -> GuardianDetailsResult | None:
    guardian = repository.get_guardian(guardian_id)

    if guardian is None:
        return None

    children = repository.get_children_for_guardian(guardian_id)

    return GuardianDetailsResult(
        id=guardian.id,
        family_id=guardian.family_id,
        full_name=guardian.full_name,
        phone=guardian.phone,
        is_active=guardian.is_active,
        children=[
            GuardianChildDetail(
                id=child.id,
                family_id=child.family_id,
                full_name=child.full_name,
                birth_date=child.birth_date,
                is_active=child.is_active,
                relationship=link.relationship,
                authorized_pickup=link.authorized_pickup,
            )
            for child, link in children
        ],
    )
