from uuid import uuid4

from church_city_kids.application.list_families import (
    list_families,
)
from church_city_kids.domain.people import Family


class FakeListFamiliesRepository:
    def __init__(self, families: list[Family]) -> None:
        self.families = families
        self.searched_name: str | None = None

    def search_active_families(self, name: str) -> list[Family]:
        self.searched_name = name
        return self.families


def test_list_families_returns_matching_families() -> None:
    family_id = uuid4()

    repository = FakeListFamiliesRepository(
        families=[
            Family(
                id=family_id,
                is_active=True,
            )
        ]
    )

    result = list_families(
        repository,
        name="maria",
    )

    assert repository.searched_name == "maria"
    assert len(result) == 1
    assert result[0].id == family_id
    assert result[0].is_active is True


def test_list_families_returns_empty_list_when_no_matches() -> None:
    repository = FakeListFamiliesRepository(families=[])

    result = list_families(
        repository,
        name="inexistente",
    )

    assert result == []
