from typing import Protocol
from uuid import UUID

from church_city_kids.domain.user import User


class ChangePasswordRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...

    def update_password_hash(
        self,
        user_id: UUID,
        password_hash: str,
    ) -> None: ...


class PasswordHasherProtocol(Protocol):
    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool: ...

    def hash(self, password: str) -> str: ...


class UserNotFoundError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
    pass


def change_password(
    user_id: UUID,
    current_password: str,
    new_password: str,
    repository: ChangePasswordRepository,
    password_hasher: PasswordHasherProtocol,
) -> None:
    user = repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise UserNotFoundError("User not found")

    if not password_hasher.verify(
        current_password,
        user.password_hash,
    ):
        raise InvalidCurrentPasswordError(
            "Current password is incorrect"
        )

    if len(new_password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    if not new_password.strip():
        raise ValueError("Password cannot contain only whitespace")

    new_password_hash = password_hasher.hash(new_password)

    repository.update_password_hash(
        user_id=user.id,
        password_hash=new_password_hash,
    )
