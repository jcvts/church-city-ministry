from uuid import UUID, uuid4

import pytest

from church_city_kids.application.update_guardian import (
    UpdateGuardianRequest,
    update_guardian,
)
from church_city_kids.domain.people import Guardian


class FakeUpdateGuardianRepository:
    def __init__(self, guardian: Guardian | None) -> None:
        self.guardian = guardian
        self.saved_guardian: Guardian | None = None

    def get_guardian(self, guardian_id: UUID) -> Guardian | None:
        if self.guardian is not None and self.guardian.id == guardian_id:
            return self.guardian
        return None

    def save_guardian(self, guardian: Guardian) -> None:
        self.saved_guardian = guardian


def test_update_guardian_changes_name_without_modifying_other_fields() -> None:
    family_id = uuid4()
    guardian_id = uuid4()

    guardian = Guardian(
        id=guardian_id,
        family_id=family_id,
        full_name="Ana Silva",
        phone="82999999999",
        is_active=True,
    )

    repository = FakeUpdateGuardianRepository(guardian)

    update_guardian(
        UpdateGuardianRequest(
            guardian_id=guardian_id,
            full_name="Ana Oliveira",
        ),
        repository,
    )

    assert repository.saved_guardian is not None
    assert repository.saved_guardian.id == guardian_id
    assert repository.saved_guardian.full_name == "Ana Oliveira"
    assert repository.saved_guardian.phone == "82999999999"
    assert repository.saved_guardian.family_id == family_id
    assert repository.saved_guardian.is_active is True


def test_update_guardian_changes_phone() -> None:
    guardian = Guardian(
        family_id=uuid4(),
        full_name="Ana Silva",
        phone="82999999999",
    )
    repository = FakeUpdateGuardianRepository(guardian)

    update_guardian(
        UpdateGuardianRequest(
            guardian_id=guardian.id,
            phone="82988888888",
        ),
        repository,
    )

    assert repository.saved_guardian is not None
    assert repository.saved_guardian.phone == "82988888888"
    assert repository.saved_guardian.full_name == "Ana Silva"


def test_update_guardian_can_remove_phone() -> None:
    guardian = Guardian(
        family_id=uuid4(),
        full_name="Ana Silva",
        phone="82999999999",
    )
    repository = FakeUpdateGuardianRepository(guardian)

    update_guardian(
        UpdateGuardianRequest(
            guardian_id=guardian.id,
            phone=None,
        ),
        repository,
    )

    assert repository.saved_guardian is not None
    assert repository.saved_guardian.phone is None
    assert repository.saved_guardian.full_name == "Ana Silva"


@pytest.mark.parametrize("invalid_name", ["", "   ", None, 123])
def test_update_guardian_rejects_invalid_name(
    invalid_name: object,
) -> None:
    guardian = Guardian(
        family_id=uuid4(),
        full_name="Ana Silva",
    )
    repository = FakeUpdateGuardianRepository(guardian)

    with pytest.raises(ValueError):
        update_guardian(
            UpdateGuardianRequest(
                guardian_id=guardian.id,
                full_name=invalid_name,
            ),
            repository,
        )

    assert guardian.full_name == "Ana Silva"
    assert repository.saved_guardian is None


def test_update_guardian_rejects_empty_patch() -> None:
    guardian = Guardian(
        family_id=uuid4(),
        full_name="Ana Silva",
    )
    repository = FakeUpdateGuardianRepository(guardian)

    with pytest.raises(ValueError, match="At least one field"):
        update_guardian(
            UpdateGuardianRequest(guardian_id=guardian.id),
            repository,
        )

    assert repository.saved_guardian is None


def test_update_guardian_rejects_invalid_phone_without_partial_update() -> None:
    guardian = Guardian(
        family_id=uuid4(),
        full_name="Ana Silva",
        phone="82999999999",
    )
    repository = FakeUpdateGuardianRepository(guardian)

    with pytest.raises(ValueError, match="Invalid guardian phone"):
        update_guardian(
            UpdateGuardianRequest(
                guardian_id=guardian.id,
                full_name="Ana Oliveira",
                phone=123,
            ),
            repository,
        )

    assert guardian.full_name == "Ana Silva"
    assert guardian.phone == "82999999999"
    assert repository.saved_guardian is None


def test_update_guardian_raises_when_guardian_does_not_exist() -> None:
    from church_city_kids.application.update_guardian import (
        GuardianNotFoundError,
    )

    repository = FakeUpdateGuardianRepository(None)

    with pytest.raises(GuardianNotFoundError):
        update_guardian(
            UpdateGuardianRequest(
                guardian_id=uuid4(),
                full_name="Ana Oliveira",
            ),
            repository,
        )

    assert repository.saved_guardian is None
