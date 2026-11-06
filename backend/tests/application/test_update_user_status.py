from uuid import uuid4

import pytest

from church_city_kids.domain.user import User


def test_deactivate_user_preserves_user_data() -> None:
    from church_city_kids.application.update_user_status import (
        update_user_status,
    )

    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="existing-hash",
        is_active=True,
        role="volunteer",
    )

    class FakeUserRepository:
        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update(self, updated_user):
            self.saved_user = updated_user

    repository = FakeUserRepository()

    update_user_status(
        user_id=user.id,
        is_active=False,
        repository=repository,
    )

    assert repository.saved_user.id == user.id
    assert repository.saved_user.username == "volunteer.maria"
    assert repository.saved_user.password_hash == "existing-hash"
    assert repository.saved_user.role == "volunteer"
    assert repository.saved_user.is_active is False


def test_reactivate_user_preserves_user_data() -> None:
    from church_city_kids.application.update_user_status import (
        update_user_status,
    )

    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="existing-hash",
        is_active=False,
        role="volunteer",
    )

    class FakeUserRepository:
        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update(self, updated_user):
            self.saved_user = updated_user

    repository = FakeUserRepository()

    update_user_status(
        user_id=user.id,
        is_active=True,
        repository=repository,
    )

    assert repository.saved_user.id == user.id
    assert repository.saved_user.username == "volunteer.maria"
    assert repository.saved_user.password_hash == "existing-hash"
    assert repository.saved_user.role == "volunteer"
    assert repository.saved_user.is_active is True


def test_update_user_status_rejects_unknown_user() -> None:
    from church_city_kids.application.update_user_status import (
        UserNotFoundError,
        update_user_status,
    )

    class FakeUserRepository:
        def get_by_id(self, user_id):
            return None

        def update(self, updated_user):
            pytest.fail("Repository.update must not be called")

    repository = FakeUserRepository()

    with pytest.raises(UserNotFoundError, match="User not found"):
        update_user_status(
            user_id=uuid4(),
            is_active=False,
            repository=repository,
        )
