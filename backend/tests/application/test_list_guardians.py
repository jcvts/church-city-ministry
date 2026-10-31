from uuid import uuid4

from church_city_kids.application.list_guardians import list_guardians
from church_city_kids.domain.people import Guardian


class FakeListGuardiansRepository:
    def __init__(self, guardians: list[Guardian]) -> None:
        self.guardians = guardians
        self.searched_name: str | None = None

    def search_active_guardians(self, name: str) -> list[Guardian]:
        self.searched_name = name
        return self.guardians


def test_list_guardians_returns_matching_guardians() -> None:
    family_id = uuid4()
    guardian_id = uuid4()

    repository = FakeListGuardiansRepository(
        guardians=[
            Guardian(
                id=guardian_id,
                family_id=family_id,
                full_name="Maria Oliveira",
                phone="82999999999",
                is_active=True,
            )
        ]
    )

    results = list_guardians(repository, name="maria")

    assert repository.searched_name == "maria"
    assert len(results) == 1

    guardian = results[0]

    assert guardian.id == guardian_id
    assert guardian.family_id == family_id
    assert guardian.full_name == "Maria Oliveira"
    assert guardian.phone == "82999999999"
    assert guardian.is_active is True


def test_list_guardians_returns_empty_list_when_no_matches() -> None:
    repository = FakeListGuardiansRepository(guardians=[])

    results = list_guardians(repository, name="unknown")

    assert results == []
    assert repository.searched_name == "unknown"
