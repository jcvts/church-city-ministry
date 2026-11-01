from datetime import date
from uuid import UUID, uuid4

import pytest

from church_city_kids.application.update_child import (
    ChildNotFoundError,
    UpdateChildRequest,
    update_child,
)
from church_city_kids.domain.people import Child


class FakeUpdateChildRepository:
    def __init__(self, child: Child | None) -> None:
        self.child = child
        self.saved_child: Child | None = None

    def get_child(self, child_id: UUID) -> Child | None:
        if self.child is not None and self.child.id == child_id:
            return self.child
        return None

    def save_child(self, child: Child) -> None:
        self.saved_child = child


def test_update_child_changes_name_without_modifying_other_fields() -> None:
    family_id = uuid4()
    child_id = uuid4()
    original_birth_date = date(2021, 5, 10)

    child = Child(
        id=child_id,
        family_id=family_id,
        full_name="Maria Silva",
        birth_date=original_birth_date,
        is_active=True,
    )

    repository = FakeUpdateChildRepository(child)

    update_child(
        UpdateChildRequest(
            child_id=child_id,
            full_name="Maria Oliveira",
        ),
        repository,
    )

    assert repository.saved_child is not None
    assert repository.saved_child.id == child_id
    assert repository.saved_child.full_name == "Maria Oliveira"

    # Fields not included in the PATCH must remain unchanged.
    assert repository.saved_child.birth_date == original_birth_date
    assert repository.saved_child.family_id == family_id
    assert repository.saved_child.is_active is True


def test_update_child_changes_birth_date_without_modifying_other_fields() -> None:
    family_id = uuid4()
    child_id = uuid4()

    child = Child(
        id=child_id,
        family_id=family_id,
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
        is_active=True,
    )

    repository = FakeUpdateChildRepository(child)

    update_child(
        UpdateChildRequest(
            child_id=child_id,
            birth_date=date(2020, 8, 15),
        ),
        repository,
    )

    assert repository.saved_child is not None
    assert repository.saved_child.birth_date == date(2020, 8, 15)
    assert repository.saved_child.full_name == "Maria Silva"
    assert repository.saved_child.family_id == family_id
    assert repository.saved_child.is_active is True


def test_update_child_raises_when_child_does_not_exist() -> None:
    child_id = uuid4()
    repository = FakeUpdateChildRepository(None)

    with pytest.raises(ChildNotFoundError):
        update_child(
            UpdateChildRequest(
                child_id=child_id,
                full_name="Maria Oliveira",
            ),
            repository,
        )

    assert repository.saved_child is None


@pytest.mark.parametrize("invalid_name", ["", "   "])
def test_update_child_rejects_blank_name(invalid_name: str) -> None:
    child = Child(
        family_id=uuid4(),
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )
    repository = FakeUpdateChildRepository(child)

    with pytest.raises(ValueError, match="Child name cannot be blank"):
        update_child(
            UpdateChildRequest(
                child_id=child.id,
                full_name=invalid_name,
            ),
            repository,
        )

    assert child.full_name == "Maria Silva"
    assert repository.saved_child is None


def test_update_child_rejects_empty_update() -> None:
    child = Child(
        family_id=uuid4(),
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )
    repository = FakeUpdateChildRepository(child)

    with pytest.raises(ValueError, match="At least one field must be provided"):
        update_child(
            UpdateChildRequest(child_id=child.id),
            repository,
        )

    assert child.full_name == "Maria Silva"
    assert child.birth_date == date(2021, 5, 10)
    assert repository.saved_child is None


def test_update_child_rejects_invalid_birth_date_without_changing_name() -> None:
    child = Child(
        family_id=uuid4(),
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )
    repository = FakeUpdateChildRepository(child)

    with pytest.raises(ValueError, match="Invalid birth date"):
        update_child(
            UpdateChildRequest(
                child_id=child.id,
                full_name="Maria Oliveira",
                birth_date="not-a-date",
            ),
            repository,
        )

    assert child.full_name == "Maria Silva"
    assert child.birth_date == date(2021, 5, 10)
    assert repository.saved_child is None
