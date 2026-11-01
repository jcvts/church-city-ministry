from dataclasses import replace
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.user import User


class UpdateUserStatusRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...

    def update(self, user: User) -> None: ...


class UserNotFoundError(Exception):
    pass


def update_user_status(
    user_id: UUID,
    is_active: bool,
    repository: UpdateUserStatusRepository,
) -> User:
    user = repository.get_by_id(user_id)

    if user is None:
        raise UserNotFoundError("User not found")

    updated_user = replace(
        user,
        is_active=is_active,
    )

    repository.update(updated_user)
    return updated_user
