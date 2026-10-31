from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Child


@dataclass(frozen=True)
class ChildResult:
    id: UUID
    family_id: UUID
    full_name: str
    birth_date: date


class ListChildrenRepository(Protocol):
    def search_active_children(self, name: str) -> list[Child]: ...


def list_children(
    repository: ListChildrenRepository,
    *,
    name: str,
) -> list[ChildResult]:
    children = repository.search_active_children(name)

    return [
        ChildResult(
            id=child.id,
            family_id=child.family_id,
            full_name=child.full_name,
            birth_date=child.birth_date,
        )
        for child in children
    ]
