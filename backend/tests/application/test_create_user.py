from uuid import UUID, uuid4

import pytest

from church_city_kids.application.create_user import (
    CreateUserRequest,
    create_user,
)
from church_city_kids.domain.user import User
from church_city_kids.infrastructure.security.passwords import PasswordHasher


class FakeCreateUserRepository:
    def __init__(self, existing_user: User | None = None) -> None:
        self.existing_user = existing_user
        self.saved_user: User | None = None

    def get_by_username(self, username: str) -> User | None:
        if (
            self.existing_user is not None
            and self.existing_user.username.lower() == username.lower()
        ):
            return self.existing_user

        return None

    def add(self, user: User) -> None:
        self.saved_user = user


def test_create_user_creates_active_volunteer_with_hashed_password() -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    result = create_user(
        CreateUserRequest(
            username="volunteer.maria",
            password="SecurePassword123!",
        ),
        repository,
        password_hasher,
    )

    assert isinstance(result, UUID)

    saved_user = repository.saved_user

    assert saved_user is not None
    assert saved_user.id == result
    assert saved_user.username == "volunteer.maria"
    assert saved_user.role == "volunteer"
    assert saved_user.is_active is True

    assert saved_user.password_hash != "SecurePassword123!"
    assert password_hasher.verify(
        "SecurePassword123!",
        saved_user.password_hash,
    )


def test_create_user_rejects_duplicate_username() -> None:
    from church_city_kids.application.create_user import (
        UsernameAlreadyExistsError,
    )

    existing_user = User(
        id=uuid4(),
        username="volunteer.maria",
        password_hash="existing-hash",
    )

    repository = FakeCreateUserRepository(existing_user)
    password_hasher = PasswordHasher()

    with pytest.raises(UsernameAlreadyExistsError):
        create_user(
            CreateUserRequest(
                username="VOLUNTEER.MARIA",
                password="AnotherSecurePassword123!",
            ),
            repository,
            password_hasher,
        )

    assert repository.saved_user is None


@pytest.mark.parametrize(
    "invalid_username",
    ["", " ", "   ", "\t", "\n"],
)
def test_create_user_rejects_blank_username(
    invalid_username: str,
) -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    with pytest.raises(ValueError, match="Username cannot be blank"):
        create_user(
            CreateUserRequest(
                username=invalid_username,
                password="SecurePassword123!",
            ),
            repository,
            password_hasher,
        )

    assert repository.saved_user is None


def test_create_user_normalizes_username_whitespace() -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    create_user(
        CreateUserRequest(
            username="  volunteer.maria  ",
            password="SecurePassword123!",
        ),
        repository,
        password_hasher,
    )

    assert repository.saved_user is not None
    assert repository.saved_user.username == "volunteer.maria"


@pytest.mark.parametrize(
    "invalid_password",
    [
        "",
        " ",
        "           ",
        "12345678",
        "Password1!",
        "short",
    ],
)
def test_create_user_rejects_short_password(
    invalid_password: str,
) -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    with pytest.raises(
        ValueError,
        match="Password must contain at least 12 characters",
    ):
        create_user(
            CreateUserRequest(
                username="volunteer.maria",
                password=invalid_password,
            ),
            repository,
            password_hasher,
        )

    assert repository.saved_user is None


def test_create_user_accepts_password_with_12_characters() -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    create_user(
        CreateUserRequest(
            username="volunteer.maria",
            password="abcdefghijkl",
        ),
        repository,
        password_hasher,
    )

    assert repository.saved_user is not None
    assert password_hasher.verify(
        "abcdefghijkl",
        repository.saved_user.password_hash,
    )


@pytest.mark.parametrize(
    "invalid_password",
    [
        " " * 12,
        "\t" * 12,
        "\n" * 12,
        " \t \n " * 3,
    ],
)
def test_create_user_rejects_whitespace_only_password(
    invalid_password: str,
) -> None:
    repository = FakeCreateUserRepository()
    password_hasher = PasswordHasher()

    with pytest.raises(
        ValueError,
        match="Password cannot contain only whitespace",
    ):
        create_user(
            CreateUserRequest(
                username="volunteer.maria",
                password=invalid_password,
            ),
            repository,
            password_hasher,
        )

    assert repository.saved_user is None
