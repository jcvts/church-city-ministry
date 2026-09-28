from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.models import (
    AttendanceModel,
    ChildModel,
    FamilyModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)


def create_attendance_dependencies(
    session: Session,
) -> tuple[UUID, UUID]:
    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()

    session.add(
        FamilyModel(
            id=family_id,
            is_active=True,
        )
    )
    session.flush()

    session.add(
        ChildModel(
            id=child_id,
            family_id=family_id,
            full_name="Test Child",
            birth_date=datetime(2021, 1, 1).date(),
            is_active=True,
        )
    )

    session.add(
        ServiceModel(
            id=service_id,
            name="Sunday Service",
            starts_at=datetime(2026, 9, 20, 19, 0),
            ends_at=None,
        )
    )

    session.add(
        RoomModel(
            id=room_id,
            name="Kids Room",
            is_active=True,
        )
    )

    session.flush()

    session.add(
        SessionModel(
            id=session_id,
            service_id=service_id,
            room_id=room_id,
            name="Kids 3-5",
            min_age_years=3,
            max_age_years=5,
            status="OPEN",
        )
    )

    session.flush()

    return child_id, session_id


def create_attendance(
    session: Session,
    *,
    checked_in_at: datetime | None = None,
) -> UUID:
    child_id, session_id = create_attendance_dependencies(session)
    attendance_id = uuid4()

    session.add(
        AttendanceModel(
            id=attendance_id,
            child_id=child_id,
            session_id=session_id,
            checked_in_at=checked_in_at
            or datetime(2026, 9, 20, 18, 50),
            checked_out_at=None,
        )
    )
    session.flush()

    return attendance_id
