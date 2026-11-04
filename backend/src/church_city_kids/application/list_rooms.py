from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import Room


@dataclass(frozen=True)
class RoomResult:
    id: UUID
    name: str
    min_age_years: int | None = None
    max_age_years: int | None = None


class ListRoomsRepository(Protocol):
    def get_active_rooms(self) -> list[Room]: ...


def list_rooms(repository: ListRoomsRepository) -> list[RoomResult]:
    rooms = repository.get_active_rooms()

    return [
        RoomResult(
            id=room.id,
            name=room.name,
            min_age_years=room.min_age_years,
            max_age_years=room.max_age_years,
        )
        for room in rooms
    ]
