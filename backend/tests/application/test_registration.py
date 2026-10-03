from datetime import date

from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)


class FakeRegistrationRepository:
    def __init__(self) -> None:
        self.families: list[Family] = []
        self.guardians: list[Guardian] = []
        self.children: list[Child] = []
        self.child_guardians: list[ChildGuardian] = []

    def add_family(self, family: Family) -> None:
        self.families.append(family)

    def add_guardian(self, guardian: Guardian) -> None:
        self.guardians.append(guardian)

    def add_child(self, child: Child) -> None:
        self.children.append(child)

    def add_child_guardian(self, link: ChildGuardian) -> None:
        self.child_guardians.append(link)


def test_register_child_creates_family_guardian_child_and_link() -> None:
    repository = FakeRegistrationRepository()

    request = RegisterChildRequest(
        child_name="Test Child",
        birth_date=date(2021, 1, 1),
        guardian_name="Test Guardian",
        guardian_phone="82999999999",
        relationship="Mother",
    )

    result = register_child(request, repository)

    assert len(repository.families) == 1
    assert len(repository.guardians) == 1
    assert len(repository.children) == 1
    assert len(repository.child_guardians) == 1

    family = repository.families[0]
    guardian = repository.guardians[0]
    child = repository.children[0]
    link = repository.child_guardians[0]

    assert child.full_name == "Test Child"
    assert child.birth_date == date(2021, 1, 1)
    assert child.family_id == family.id

    assert guardian.full_name == "Test Guardian"
    assert guardian.phone == "82999999999"
    assert guardian.family_id == family.id

    assert link.child_id == child.id
    assert link.guardian_id == guardian.id
    assert link.relationship == "Mother"
    assert link.authorized_pickup is True

    assert result.family_id == family.id
    assert result.child_id == child.id
    assert result.guardian_id == guardian.id
