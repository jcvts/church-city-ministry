from datetime import date, datetime

from church_city_kids.domain.people import Child, Family, Guardian, Volunteer
from church_city_kids.domain.scheduling import (
    Room,
    Service,
    Session,
    SessionStatus,
    create_session,
)


def make_family() -> Family:
    return Family()


def make_guardian(family: Family, *, phone: str | None = None) -> Guardian:
    return Guardian(family_id=family.id, full_name="Ana Guardian", phone=phone)


def make_child(
    family: Family,
    *,
    birth_date: date,
    full_name: str = "Joao Child",
) -> Child:
    return Child(family_id=family.id, full_name=full_name, birth_date=birth_date)


def make_service(
    *,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Service:
    if starts_at is None:
        starts_at = datetime(2026, 9, 20, 10, 0)
    return Service(name="Sunday morning", starts_at=starts_at, ends_at=ends_at)


def make_room(name: str = "Room A") -> Room:
    return Room(name=name)


def make_open_session(
    service: Service,
    room: Room,
    *,
    min_age_years: int = 3,
    max_age_years: int = 5,
    name: str = "Kids 3-5",
    existing: list[Session] | None = None,
) -> Session:
    sessions = existing if existing is not None else []
    session = create_session(
        service,
        room,
        name,
        min_age_years,
        max_age_years,
        sessions,
        status=SessionStatus.OPEN,
    )
    return session


def make_volunteer(full_name: str = "Maria Volunteer") -> Volunteer:
    return Volunteer(full_name=full_name)
