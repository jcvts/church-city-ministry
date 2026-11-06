from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.errors import RoomNameAlreadyExistsError
from church_city_kids.domain.scheduling import Room


class _UnsetType:
    pass


_UNSET = _UnsetType()


@dataclass(frozen=True)
class UpdateRoomRequest:
    room_id: UUID
    name: str | _UnsetType = _UNSET
    min_age_years: int | None | _UnsetType = _UNSET
    max_age_years: int | None | _UnsetType = _UNSET


class UpdateRoomRepository(Protocol):
    def get_room(self, room_id: UUID) -> Room | None: ...

    def room_name_exists(
        self,
        name: str,
        exclude_room_id: UUID,
    ) -> bool: ...

    def save_room(self, room: Room) -> None: ...


class RoomNotFoundError(Exception):
    pass


def update_room(
    request: UpdateRoomRequest,
    repository: UpdateRoomRepository,
) -> None:
    if (
        isinstance(request.name, _UnsetType)
        and isinstance(request.min_age_years, _UnsetType)
        and isinstance(request.max_age_years, _UnsetType)
    ):
        raise ValueError("At least one field must be provided")

    # Validate supplied fields before modifying the entity.
    if not isinstance(request.name, _UnsetType):
        if not isinstance(request.name, str):
            raise ValueError("Invalid room name")

        if not request.name.strip():
            raise ValueError("Room name cannot be blank")

        if repository.room_name_exists(
            request.name,
            request.room_id,
        ):
            raise RoomNameAlreadyExistsError()

    for field_name, value in (
        ("min_age_years", request.min_age_years),
        ("max_age_years", request.max_age_years),
    ):
        if not isinstance(value, _UnsetType) and value is not None:
            if type(value) is not int or value < 0:
                raise ValueError(f"Invalid {field_name}")

    room = repository.get_room(request.room_id)

    if room is None:
        raise RoomNotFoundError()

    new_name = request.name.strip() if isinstance(request.name, str) else room.name

    if isinstance(request.min_age_years, _UnsetType):
        new_min_age = room.min_age_years
    else:
        new_min_age = request.min_age_years

    if isinstance(request.max_age_years, _UnsetType):
        new_max_age = room.max_age_years
    else:
        new_max_age = request.max_age_years

    # Validate the complete resulting configuration before mutation.
    updated_room = Room(
        id=room.id,
        name=new_name,
        is_active=room.is_active,
        min_age_years=new_min_age,
        max_age_years=new_max_age,
    )

    room.name = updated_room.name
    room.min_age_years = updated_room.min_age_years
    room.max_age_years = updated_room.max_age_years

    repository.save_room(room)
