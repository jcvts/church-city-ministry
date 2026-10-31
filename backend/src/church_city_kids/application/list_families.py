from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Family


@dataclass(frozen=True)
class FamilyResult:
    id: UUID
    is_active: bool


class ListFamiliesRepository(Protocol):
    def search_active_families(self, name: str) -> list[Family]: ...


def list_families(
    repository: ListFamiliesRepository,
    *,
    name: str,
) -> list[FamilyResult]:
    families = repository.search_active_families(name)

    return [
        FamilyResult(
            id=family.id,
            is_active=family.is_active,
        )
        for family in families
    ]
