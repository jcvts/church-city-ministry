from typing import Protocol

from church_city_kids.domain.user import User


class ListUsersRepository(Protocol):
    def list_all(self) -> list[User]: ...


def list_users(
    repository: ListUsersRepository,
) -> list[User]:
    return repository.list_all()
