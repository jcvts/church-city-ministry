from uuid import UUID, uuid4

import pytest

from church_city_kids.application.update_room import (
    RoomNameAlreadyExistsError,
    RoomNotFoundError,
    UpdateRoomRequest,
    update_room,
)
from church_city_kids.domain.errors import InvalidAgeRangeError
from church_city_kids.domain.scheduling import Room


class FakeUpdateRoomRepository:
    def __init__(self, rooms: list[Room]) -> None:
        self.rooms = rooms
        self.saved_room: Room | None = None

    def get_room(self, room_id: UUID) -> Room | None:
        return next(
            (room for room in self.rooms if room.id == room_id),
            None,
        )

    def room_name_exists(
        self,
        name: str,
        exclude_room_id: UUID,
    ) -> bool:
        from church_city_kids.domain.scheduling import normalize_room_name

        normalized_name = normalize_room_name(name)

        return any(
            room.id != exclude_room_id
            and normalize_room_name(room.name) == normalized_name
            for room in self.rooms
        )

    def save_room(self, room: Room) -> None:
        self.saved_room = room


def create_room() -> Room:
    return Room(
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
    )


def test_update_room_changes_name() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    update_room(
        UpdateRoomRequest(
            room_id=room.id,
            name="Sala Infantil",
        ),
        repository,
    )

    assert repository.saved_room is not None
    assert repository.saved_room.name == "Sala Infantil"
    assert repository.saved_room.min_age_years == 3
    assert repository.saved_room.max_age_years == 5


def test_update_room_changes_age_range() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    update_room(
        UpdateRoomRequest(
            room_id=room.id,
            min_age_years=2,
            max_age_years=4,
        ),
        repository,
    )

    assert repository.saved_room is not None
    assert repository.saved_room.min_age_years == 2
    assert repository.saved_room.max_age_years == 4
    assert repository.saved_room.name == "Sala 1"


def test_update_room_preserves_unspecified_fields() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    update_room(
        UpdateRoomRequest(
            room_id=room.id,
            max_age_years=6,
        ),
        repository,
    )

    assert repository.saved_room is not None
    assert repository.saved_room.name == "Sala 1"
    assert repository.saved_room.min_age_years == 3
    assert repository.saved_room.max_age_years == 6


def test_update_room_rejects_duplicate_name() -> None:
    room = create_room()
    another_room = Room(name="Sala 2")
    repository = FakeUpdateRoomRepository([room, another_room])

    with pytest.raises(RoomNameAlreadyExistsError):
        update_room(
            UpdateRoomRequest(
                room_id=room.id,
                name="  sala   2  ",
            ),
            repository,
        )

    assert repository.saved_room is None


def test_update_room_rejects_blank_name() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    with pytest.raises(ValueError, match="Room name cannot be blank"):
        update_room(
            UpdateRoomRequest(room_id=room.id, name="  "),
            repository,
        )

    assert room.name == "Sala 1"
    assert repository.saved_room is None


def test_update_room_rejects_invalid_age_range() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    with pytest.raises(InvalidAgeRangeError):
        update_room(
            UpdateRoomRequest(
                room_id=room.id,
                min_age_years=7,
                max_age_years=5,
            ),
            repository,
        )

    assert room.min_age_years == 3
    assert room.max_age_years == 5
    assert repository.saved_room is None


def test_update_room_rejects_negative_age() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    with pytest.raises(ValueError):
        update_room(
            UpdateRoomRequest(
                room_id=room.id,
                min_age_years=-1,
            ),
            repository,
        )

    assert repository.saved_room is None


def test_update_room_rejects_empty_update() -> None:
    room = create_room()
    repository = FakeUpdateRoomRepository([room])

    with pytest.raises(ValueError, match="At least one field"):
        update_room(
            UpdateRoomRequest(room_id=room.id),
            repository,
        )

    assert repository.saved_room is None


def test_update_room_rejects_missing_room() -> None:
    repository = FakeUpdateRoomRepository([])

    with pytest.raises(RoomNotFoundError):
        update_room(
            UpdateRoomRequest(
                room_id=uuid4(),
                name="Sala Nova",
            ),
            repository,
        )

    assert repository.saved_room is None
