from datetime import date
from uuid import uuid4

from church_city_kids.application.list_children import list_children
from church_city_kids.domain.people import Child


class FakeListChildrenRepository:
    def __init__(self, children: list[Child]) -> None:
        self.children = children
        self.searched_name: str | None = None

    def search_active_children(self, name: str) -> list[Child]:
        self.searched_name = name
        return self.children


def test_list_children_returns_matching_children() -> None:
    family_id = uuid4()
    child = Child(
        family_id=family_id,
        full_name="Maria Silva",
        birth_date=date(2020, 5, 12),
    )
    repository = FakeListChildrenRepository([child])

    result = list_children(repository, name="maria")

    assert repository.searched_name == "maria"
    assert len(result) == 1
    assert result[0].id == child.id
    assert result[0].family_id == family_id
    assert result[0].full_name == "Maria Silva"
    assert result[0].birth_date == date(2020, 5, 12)