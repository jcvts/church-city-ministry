from datetime import date
from uuid import uuid4

from church_city_kids.application.get_child_details import get_child_details
from church_city_kids.domain.people import Child, ChildGuardian, Guardian


class FakeGetChildDetailsRepository:
    def __init__(
        self,
        child: Child,
        guardians: list[tuple[Guardian, ChildGuardian]],
    ) -> None:
        self.child = child
        self.guardians = guardians

    def get_child(self, child_id):
        return self.child if child_id == self.child.id else None

    def get_guardians_for_child(self, child_id):
        return self.guardians if child_id == self.child.id else []


def test_get_child_details_returns_child_and_guardians() -> None:
    family_id = uuid4()

    child = Child(
        family_id=family_id,
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )

    guardian = Guardian(
        family_id=family_id,
        full_name="Ana Silva",
        phone="82999999999",
    )

    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        relationship="Mother",
        authorized_pickup=True,
    )

    repository = FakeGetChildDetailsRepository(
        child=child,
        guardians=[(guardian, link)],
    )

    result = get_child_details(repository, child_id=child.id)

    assert result is not None
    assert result.id == child.id
    assert result.family_id == family_id
    assert result.full_name == "Maria Silva"
    assert result.birth_date == date(2021, 5, 10)

    assert len(result.guardians) == 1

    guardian_result = result.guardians[0]

    assert guardian_result.id == guardian.id
    assert guardian_result.full_name == "Ana Silva"
    assert guardian_result.phone == "82999999999"
    assert guardian_result.relationship == "Mother"
    assert guardian_result.authorized_pickup is True
    assert guardian_result.is_active is True


def test_get_child_details_returns_none_when_child_does_not_exist() -> None:
    family_id = uuid4()

    child = Child(
        family_id=family_id,
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )

    repository = FakeGetChildDetailsRepository(
        child=child,
        guardians=[],
    )

    result = get_child_details(
        repository,
        child_id=uuid4(),
    )

    assert result is None
