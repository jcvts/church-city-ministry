from uuid import UUID, uuid4

import pytest

from church_city_kids.application.update_family import (
    UpdateFamilyRequest,
    update_family,
)
from church_city_kids.domain.people import Family


class FakeUpdateFamilyRepository:
    def __init__(self, family: Family | None) -> None:
        self.family = family
        self.saved_family: Family | None = None

    def get_family(self, family_id: UUID) -> Family | None:
        if self.family is not None and self.family.id == family_id:
            return self.family
        return None

    def save_family(self, family: Family) -> None:
        self.saved_family = family


def test_update_family_can_deactivate_family() -> None:
    family = Family(
        id=uuid4(),
        is_active=True,
    )
    repository = FakeUpdateFamilyRepository(family)

    update_family(
        UpdateFamilyRequest(
            family_id=family.id,
            is_active=False,
        ),
        repository,
    )

    assert repository.saved_family is not None
    assert repository.saved_family.id == family.id
    assert repository.saved_family.is_active is False


def test_update_family_can_reactivate_family() -> None:
    family = Family(is_active=False)
    repository = FakeUpdateFamilyRepository(family)

    update_family(
        UpdateFamilyRequest(
            family_id=family.id,
            is_active=True,
        ),
        repository,
    )

    assert repository.saved_family is not None
    assert repository.saved_family.is_active is True


@pytest.mark.parametrize("invalid_status", [None, 0, 1, "true", "false"])
def test_update_family_rejects_invalid_status(
    invalid_status: object,
) -> None:
    family = Family(is_active=True)
    repository = FakeUpdateFamilyRepository(family)

    with pytest.raises(ValueError, match="Invalid family status"):
        update_family(
            UpdateFamilyRequest(
                family_id=family.id,
                is_active=invalid_status,  # type: ignore[arg-type]
            ),
            repository,
        )

    assert family.is_active is True
    assert repository.saved_family is None


def test_update_family_raises_when_family_does_not_exist() -> None:
    from church_city_kids.application.update_family import FamilyNotFoundError

    repository = FakeUpdateFamilyRepository(None)

    with pytest.raises(FamilyNotFoundError):
        update_family(
            UpdateFamilyRequest(
                family_id=uuid4(),
                is_active=False,
            ),
            repository,
        )

    assert repository.saved_family is None
