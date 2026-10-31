from datetime import date
from uuid import UUID, uuid4

from church_city_kids.application.get_family_details import (
    get_family_details,
)
from church_city_kids.domain.people import Child, Family, Guardian


class FakeGetFamilyDetailsRepository:
    def __init__(
        self,
        family: Family | None,
        children: list[Child],
        guardians: list[Guardian],
    ) -> None:
        self.family = family
        self.children = children
        self.guardians = guardians

    def get_family(self, family_id: UUID) -> Family | None:
        if self.family is not None and self.family.id == family_id:
            return self.family
        return None

    def get_children_for_family(self, family_id: UUID) -> list[Child]:
        return self.children

    def get_guardians_for_family(self, family_id: UUID) -> list[Guardian]:
        return self.guardians


def test_get_family_details_returns_children_and_guardians() -> None:
    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    repository = FakeGetFamilyDetailsRepository(
        family=Family(id=family_id, is_active=True),
        children=[
            Child(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            )
        ],
        guardians=[
            Guardian(
                id=guardian_id,
                family_id=family_id,
                full_name="João Silva",
                phone="82999999999",
                is_active=True,
            )
        ],
    )

    result = get_family_details(
        repository,
        family_id=family_id,
    )

    assert result is not None
    assert result.id == family_id
    assert result.is_active is True

    assert len(result.children) == 1
    assert result.children[0].id == child_id
    assert result.children[0].full_name == "Maria Silva"
    assert result.children[0].birth_date == date(2021, 5, 10)

    assert len(result.guardians) == 1
    assert result.guardians[0].id == guardian_id
    assert result.guardians[0].full_name == "João Silva"
    assert result.guardians[0].phone == "82999999999"
