from uuid import uuid4

import pytest

from church_city_kids.application.change_password import (
    InvalidCurrentPasswordError,
    UserNotFoundError,
    change_password,
)
from church_city_kids.domain.user import User


def test_change_password_updates_password_hash() -> None:
    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="old-hash",
        role="volunteer",
        is_active=True,
    )

    class FakeUserRepository:
        def __init__(self) -> None:
            self.updated_user: User | None = None

        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update_password_hash(self, user_id, password_hash):
            self.updated_user = User(
                id=user.id,
                username=user.username,
                password_hash=password_hash,
                role=user.role,
                is_active=user.is_active,
            )

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            return password == "CurrentPassword123!" and password_hash == "old-hash"

        def hash(self, password):
            assert password == "NewSecurePassword123!"
            return "new-hash"

    repository = FakeUserRepository()

    change_password(
        user_id=user.id,
        current_password="CurrentPassword123!",
        new_password="NewSecurePassword123!",
        repository=repository,
        password_hasher=FakePasswordHasher(),
    )

    assert repository.updated_user is not None
    assert repository.updated_user.password_hash == "new-hash"
    assert repository.updated_user.username == "volunteer.maria"
    assert repository.updated_user.role == "volunteer"
    assert repository.updated_user.is_active is True


def test_change_password_rejects_incorrect_current_password() -> None:
    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="old-hash",
        role="volunteer",
        is_active=True,
    )

    class FakeUserRepository:
        def __init__(self) -> None:
            self.update_called = False

        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update_password_hash(self, user_id, password_hash):
            self.update_called = True

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            return False

        def hash(self, password):
            pytest.fail("Password must not be hashed when verification fails")

    repository = FakeUserRepository()

    with pytest.raises(InvalidCurrentPasswordError):
        change_password(
            user_id=user.id,
            current_password="WrongPassword123!",
            new_password="NewSecurePassword123!",
            repository=repository,
            password_hasher=FakePasswordHasher(),
        )

    assert repository.update_called is False


def test_change_password_rejects_short_new_password() -> None:
    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="old-hash",
        role="volunteer",
        is_active=True,
    )

    class FakeUserRepository:
        def __init__(self) -> None:
            self.update_called = False

        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update_password_hash(self, user_id, password_hash):
            self.update_called = True

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            return True

        def hash(self, password):
            pytest.fail("Invalid password must not be hashed")

    repository = FakeUserRepository()

    with pytest.raises(ValueError):
        change_password(
            user_id=user.id,
            current_password="CurrentPassword123!",
            new_password="Short123!",
            repository=repository,
            password_hasher=FakePasswordHasher(),
        )

    assert repository.update_called is False


def test_change_password_rejects_whitespace_only_new_password() -> None:
    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="old-hash",
        role="volunteer",
        is_active=True,
    )

    class FakeUserRepository:
        def __init__(self) -> None:
            self.update_called = False

        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update_password_hash(self, user_id, password_hash):
            self.update_called = True

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            return True

        def hash(self, password):
            pytest.fail("Invalid password must not be hashed")

    repository = FakeUserRepository()

    with pytest.raises(ValueError):
        change_password(
            user_id=user.id,
            current_password="CurrentPassword123!",
            new_password="            ",
            repository=repository,
            password_hasher=FakePasswordHasher(),
        )

    assert repository.update_called is False


def test_change_password_rejects_nonexistent_user() -> None:
    class FakeUserRepository:
        def get_by_id(self, user_id):
            return None

        def update_password_hash(self, user_id, password_hash):
            pytest.fail("Nonexistent user must not be updated")

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            pytest.fail("Password must not be verified for nonexistent user")

        def hash(self, password):
            pytest.fail("Password must not be hashed for nonexistent user")

    with pytest.raises(UserNotFoundError):
        change_password(
            user_id=uuid4(),
            current_password="CurrentPassword123!",
            new_password="NewSecurePassword123!",
            repository=FakeUserRepository(),
            password_hasher=FakePasswordHasher(),
        )


def test_change_password_rejects_inactive_user() -> None:
    user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="old-hash",
        role="volunteer",
        is_active=False,
    )

    class FakeUserRepository:
        def get_by_id(self, user_id):
            return user if user_id == user.id else None

        def update_password_hash(self, user_id, password_hash):
            pytest.fail("Inactive user must not be updated")

    class FakePasswordHasher:
        def verify(self, password, password_hash):
            pytest.fail("Inactive user's password must not be verified")

        def hash(self, password):
            pytest.fail("Inactive user's password must not be hashed")

    with pytest.raises(UserNotFoundError):
        change_password(
            user_id=user.id,
            current_password="CurrentPassword123!",
            new_password="NewSecurePassword123!",
            repository=FakeUserRepository(),
            password_hasher=FakePasswordHasher(),
        )
