from datetime import date
from uuid import uuid4

import pytest

from church_city_kids.application.add_child_guardian import (
    AddChildGuardianRequest,
    ChildNotFoundError,
    GuardianNotFoundError,
    add_child_guardian,
)
from church_city_kids.domain.errors import DuplicateChildGuardianError
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)


class FakeAddChildGuardianRepository:
    def __init__(
        self,
        child: Child,
        guardian: Guardian,
    ) -> None:
        self.child = child
        self.guardian = guardian
        self.links: list[ChildGuardian] = []

    def get_child(self, child_id):
        return self.child if self.child.id == child_id else None

    def get_guardian(self, guardian_id):
        return self.guardian if self.guardian.id == guardian_id else None

    def get_child_guardians(self, child_id):
        return [
            link
            for link in self.links
            if link.child_id == child_id
        ]

    def add_child_guardian(self, link: ChildGuardian) -> None:
        self.links.append(link)


def test_add_existing_guardian_from_another_family() -> None:
    child_family = Family()
    guardian_family = Family()

    child = Child(
        family_id=child_family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=guardian_family.id,
        full_name="Maria Silva",
    )

    repository = FakeAddChildGuardianRepository(child, guardian)

    result = add_child_guardian(
        AddChildGuardianRequest(
            child_id=child.id,
            guardian_id=guardian.id,
            relationship="Grandmother",
            authorized_pickup=True,
        ),
        repository,
    )

    assert len(repository.links) == 1

    link = repository.links[0]

    assert link.child_id == child.id
    assert link.guardian_id == guardian.id
    assert link.relationship == "Grandmother"
    assert link.authorized_pickup is True

    assert result.link_id == link.id


def test_add_existing_guardian_rejects_duplicate_link() -> None:
    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )

    repository = FakeAddChildGuardianRepository(child, guardian)

    existing_link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )
    repository.links.append(existing_link)

    with pytest.raises(DuplicateChildGuardianError):
        add_child_guardian(
            AddChildGuardianRequest(
                child_id=child.id,
                guardian_id=guardian.id,
                relationship="Mother",
                authorized_pickup=True,
            ),
            repository,
        )

    assert repository.links == [existing_link]


def test_add_child_guardian_rejects_unknown_child() -> None:
    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )

    repository = FakeAddChildGuardianRepository(child, guardian)

    with pytest.raises(ChildNotFoundError):
        add_child_guardian(
            AddChildGuardianRequest(
                child_id=uuid4(),
                guardian_id=guardian.id,
                authorized_pickup=True,
            ),
            repository,
        )

    assert repository.links == []


def test_add_child_guardian_rejects_unknown_guardian() -> None:
    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=family.id,
        full_name="Maria Silva",
    )

    repository = FakeAddChildGuardianRepository(child, guardian)

    with pytest.raises(GuardianNotFoundError):
        add_child_guardian(
            AddChildGuardianRequest(
                child_id=child.id,
                guardian_id=uuid4(),
                authorized_pickup=True,
            ),
            repository,
        )

    assert repository.links == []
