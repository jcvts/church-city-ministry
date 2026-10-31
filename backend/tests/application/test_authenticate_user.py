from uuid import uuid4

from church_city_kids.application.authenticate_user import (
    authenticate_user,
)
from church_city_kids.domain.user import User
from church_city_kids.infrastructure.security.passwords import PasswordHasher


class FakeUserRepository:
    def __init__(self, user: User) -> None:
        self.user = user

    def get_by_username(self, username: str) -> User | None:
        if username.lower() == self.user.username.lower():
            return self.user
        return None


def test_authenticate_user_with_valid_credentials() -> None:
    password_hasher = PasswordHasher()

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash=password_hasher.hash("SecurePassword123!"),
        is_active=True,
    )

    repository = FakeUserRepository(user)

    authenticated_user = authenticate_user(
        username="reception.admin",
        password="SecurePassword123!",
        repository=repository,
        password_hasher=password_hasher,
    )

    assert authenticated_user == user


def test_authenticate_user_rejects_incorrect_password() -> None:
    password_hasher = PasswordHasher()

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash=password_hasher.hash("SecurePassword123!"),
        is_active=True,
    )

    repository = FakeUserRepository(user)

    authenticated_user = authenticate_user(
        username="reception.admin",
        password="WrongPassword123!",
        repository=repository,
        password_hasher=password_hasher,
    )

    assert authenticated_user is None


def test_authenticate_user_rejects_inactive_user() -> None:
    password_hasher = PasswordHasher()

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash=password_hasher.hash("SecurePassword123!"),
        is_active=False,
    )

    repository = FakeUserRepository(user)

    authenticated_user = authenticate_user(
        username="reception.admin",
        password="SecurePassword123!",
        repository=repository,
        password_hasher=password_hasher,
    )

    assert authenticated_user is None


def test_authenticate_user_rejects_unknown_username() -> None:
    password_hasher = PasswordHasher()

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash=password_hasher.hash("SecurePassword123!"),
        is_active=True,
    )

    repository = FakeUserRepository(user)

    authenticated_user = authenticate_user(
        username="unknown.user",
        password="SecurePassword123!",
        repository=repository,
        password_hasher=password_hasher,
    )

    assert authenticated_user is None
