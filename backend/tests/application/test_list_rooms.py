from uuid import uuid4

from church_city_kids.application.list_rooms import list_rooms
from church_city_kids.domain.scheduling import Room


class FakeListRoomsRepository:
    def __init__(self, rooms: list[Room]) -> None:
        self.rooms = rooms

    def get_active_rooms(self) -> list[Room]:
        return [room for room in self.rooms if room.is_active]


def test_list_rooms_returns_active_rooms() -> None:
    active_room = Room(
        id=uuid4(),
        name="Sala Infantil",
        is_active=True,
        min_age_years=3,
        max_age_years=5,
    )

    inactive_room = Room(
        id=uuid4(),
        name="Sala Antiga",
        is_active=False,
    )

    repository = FakeListRoomsRepository(
        rooms=[active_room, inactive_room],
    )

    result = list_rooms(repository)

    assert len(result) == 1
    assert result[0].id == active_room.id
    assert result[0].name == "Sala Infantil"
    assert result[0].min_age_years == 3
    assert result[0].max_age_years == 5


def test_list_rooms_supports_rooms_without_age_ranges() -> None:
    room = Room(
        id=uuid4(),
        name="Sala sem configuração",
    )

    repository = FakeListRoomsRepository(rooms=[room])

    result = list_rooms(repository)

    assert len(result) == 1
    assert result[0].min_age_years is None
    assert result[0].max_age_years is None
