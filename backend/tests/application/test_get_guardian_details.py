from datetime import date
from uuid import UUID, uuid4

from church_city_kids.application.get_guardian_details import (
    get_guardian_details,
)
from church_city_kids.domain.people import Child, ChildGuardian, Guardian


class FakeGetGuardianDetailsRepository:
    def __init__(
        self,
        guardian: Guardian | None,
        children: list[tuple[Child, ChildGuardian]],
    ) -> None:
        self.guardian = guardian
        self.children = children

    def get_guardian(self, guardian_id: UUID) -> Guardian | None:
        if self.guardian is not None and self.guardian.id == guardian_id:
            return self.guardian
        return None

    def get_children_for_guardian(
        self,
        guardian_id: UUID,
    ) -> list[tuple[Child, ChildGuardian]]:
        return self.children


def test_get_guardian_details_returns_children_across_families() -> None:
    guardian_id = uuid4()
    guardian_family_id = uuid4()
    other_family_id = uuid4()

    first_child_id = uuid4()
    second_child_id = uuid4()

    repository = FakeGetGuardianDetailsRepository(
        guardian=Guardian(
            id=guardian_id,
            family_id=guardian_family_id,
            full_name="Maria Oliveira",
            phone="82999999999",
            is_active=True,
        ),
        children=[
            (
                Child(
                    id=first_child_id,
                    family_id=guardian_family_id,
                    full_name="Ana Oliveira",
                    birth_date=date(2020, 5, 10),
                ),
                ChildGuardian(
                    child_id=first_child_id,
                    guardian_id=guardian_id,
                    relationship="Mother",
                    authorized_pickup=True,
                ),
            ),
            (
                Child(
                    id=second_child_id,
                    family_id=other_family_id,
                    full_name="Pedro Silva",
                    birth_date=date(2021, 8, 15),
                ),
                ChildGuardian(
                    child_id=second_child_id,
                    guardian_id=guardian_id,
                    relationship="Aunt",
                    authorized_pickup=False,
                ),
            ),
        ],
    )

    result = get_guardian_details(
        repository,
        guardian_id=guardian_id,
    )

    assert result is not None
    assert result.id == guardian_id
    assert result.family_id == guardian_family_id
    assert result.full_name == "Maria Oliveira"
    assert result.phone == "82999999999"
    assert result.is_active is True

    assert len(result.children) == 2

    first_child = result.children[0]
    assert first_child.id == first_child_id
    assert first_child.family_id == guardian_family_id
    assert first_child.full_name == "Ana Oliveira"
    assert first_child.relationship == "Mother"
    assert first_child.authorized_pickup is True

    second_child = result.children[1]
    assert second_child.id == second_child_id
    assert second_child.family_id == other_family_id
    assert second_child.full_name == "Pedro Silva"
    assert second_child.relationship == "Aunt"
    assert second_child.authorized_pickup is False
