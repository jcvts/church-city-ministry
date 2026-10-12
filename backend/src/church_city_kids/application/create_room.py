from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import Room


@dataclass(frozen=True)
class CreateRoomRequest:
    name: str


@dataclass(frozen=True)
class CreateRoomResult:
    room_id: UUID


class CreateRoomRepository(Protocol):
    def add_room(self, room: Room) -> None: ...


def create_room(
    request: CreateRoomRequest,
    repository: CreateRoomRepository,
) -> CreateRoomResult:
    room = Room(name=request.name)

    repository.add_room(room)

    return CreateRoomResult(room_id=room.id)
