from church_city_kids.application.create_room import (
    CreateRoomRequest,
    create_room,
)
from church_city_kids.domain.scheduling import Room


class FakeCreateRoomRepository:
    def __init__(self) -> None:
        self.added_rooms: list[Room] = []

    def add_room(self, room: Room) -> None:
        self.added_rooms.append(room)


def test_create_room_creates_room() -> None:
    repository = FakeCreateRoomRepository()

    result = create_room(
        CreateRoomRequest(name="Kids 3-5"),
        repository,
    )

    assert len(repository.added_rooms) == 1

    room = repository.added_rooms[0]

    assert room.id == result.room_id
    assert room.name == "Kids 3-5"
    assert room.is_active is True
