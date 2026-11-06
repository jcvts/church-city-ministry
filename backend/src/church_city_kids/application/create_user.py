from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from church_city_kids.domain.user import User


@dataclass(frozen=True)
class CreateUserRequest:
    username: str
    password: str


class CreateUserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...

    def add(self, user: User) -> None: ...


class PasswordHasherProtocol(Protocol):
    def hash(self, password: str) -> str: ...


class UsernameAlreadyExistsError(Exception):
    pass


def create_user(
    request: CreateUserRequest,
    repository: CreateUserRepository,
    password_hasher: PasswordHasherProtocol,
) -> UUID:
    username = request.username.strip()

    if not username:
        raise ValueError("Username cannot be blank")

    if len(request.password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    if not request.password.strip():
        raise ValueError("Password cannot contain only whitespace")

    existing_user = repository.get_by_username(username)

    if existing_user is not None:
        raise UsernameAlreadyExistsError("Username already exists")

    user = User(
        id=uuid4(),
        username=username,
        password_hash=password_hasher.hash(request.password),
        is_active=True,
        role="volunteer",
    )

    repository.add(user)

    return user.id
