import pytest

from church_city_kids.application.create_room import (
    CreateRoomRequest,
    create_room,
)
from church_city_kids.domain.errors import RoomNameAlreadyExistsError
from church_city_kids.domain.scheduling import Room


class FakeCreateRoomRepository:
    def __init__(self) -> None:
        self.added_rooms: list[Room] = []

    def add_room(self, room: Room) -> None:
        self.added_rooms.append(room)

    def room_name_exists(self, name: str) -> bool:
        normalized_name = " ".join(name.split()).casefold()

        return any(
            " ".join(room.name.split()).casefold() == normalized_name
            for room in self.added_rooms
        )


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


def test_create_room_rejects_duplicate_name() -> None:
    class FakeRoomRepository:
        def __init__(self) -> None:
            self.rooms = [Room(name="Sala Infantil")]

        def room_name_exists(self, name: str) -> bool:
            return any(
                " ".join(room.name.split()).casefold()
                == " ".join(name.split()).casefold()
                for room in self.rooms
            )

        def add_room(self, room: Room) -> None:
            self.rooms.append(room)

    repository = FakeRoomRepository()

    with pytest.raises(RoomNameAlreadyExistsError):
        create_room(
            CreateRoomRequest(name="  sala   infantil  "),
            repository,
        )

    assert len(repository.rooms) == 1
