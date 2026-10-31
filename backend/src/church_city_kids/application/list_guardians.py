from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Guardian


@dataclass(frozen=True)
class GuardianResult:
    id: UUID
    family_id: UUID
    full_name: str
    phone: str | None
    is_active: bool


class ListGuardiansRepository(Protocol):
    def search_active_guardians(
        self,
        name: str,
    ) -> list[Guardian]: ...


def list_guardians(
    repository: ListGuardiansRepository,
    *,
    name: str,
) -> list[GuardianResult]:
    guardians = repository.search_active_guardians(name)

    return [
        GuardianResult(
            id=guardian.id,
            family_id=guardian.family_id,
            full_name=guardian.full_name,
            phone=guardian.phone,
            is_active=guardian.is_active,
        )
        for guardian in guardians
    ]
