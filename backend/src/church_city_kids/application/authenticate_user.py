from typing import Protocol

from church_city_kids.domain.user import User


class UserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...


class PasswordVerifier(Protocol):
    def verify(self, password: str, password_hash: str) -> bool: ...


def authenticate_user(
    username: str,
    password: str,
    repository: UserRepository,
    password_hasher: PasswordVerifier,
) -> User | None:
    user = repository.get_by_username(username)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not password_hasher.verify(password, user.password_hash):
        return None

    return user
