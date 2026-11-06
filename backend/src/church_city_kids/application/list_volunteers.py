from typing import Protocol

from church_city_kids.domain.people import Volunteer


class ListVolunteersRepository(Protocol):
    def list_all(self) -> list[Volunteer]: ...


def list_volunteers(
    repository: ListVolunteersRepository,
) -> list[Volunteer]:
    return repository.list_all()
