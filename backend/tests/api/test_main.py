from collections.abc import Generator
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import get_db_session
from church_city_kids.api.main import app
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    AttendanceModel,
    Base,
    ChildGuardianModel,
    ChildModel,
    FamilyModel,
    GuardianModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)


def create_check_in_scenario(
    session: Session,
    *,
    child_is_active: bool = True,
    family_is_active: bool = True,
    session_status: str = "open",
    child_birth_date: date = date(2021, 5, 10),
) -> tuple[UUID, UUID]:
    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()

    session.add_all(
        [
            FamilyModel(id=family_id, is_active=family_is_active),
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 17, 9, 0),
                ends_at=datetime(2026, 10, 17, 12, 0),
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                normalized_name="sala infantil",
                is_active=True,
            ),
        ]
    )
    session.flush()

    session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=child_birth_date,
                is_active=child_is_active,
            ),
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Infantil",
                min_age_years=3,
                max_age_years=5,
                status=session_status,
            ),
        ]
    )
    session.commit()

    return child_id, session_id


def create_authorized_guardian(
    session: Session,
    child_id: UUID,
) -> UUID:
    child = session.get(ChildModel, child_id)
    assert child is not None

    guardian_id = uuid4()

    session.add(
        GuardianModel(
            id=guardian_id,
            family_id=child.family_id,
            full_name="João Silva",
            is_active=True,
        )
    )
    session.flush()

    session.add(
        ChildGuardianModel(
            id=uuid4(),
            child_id=child_id,
            guardian_id=guardian_id,
            relationship="father",
            authorized_pickup=True,
        )
    )
    session.commit()

    return guardian_id


@pytest.fixture
def api_client(
    tmp_path: Path,
) -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    def override_get_db_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(
            app,
            raise_server_exceptions=False,
        ) as client:
            with Session(engine) as verification_session:
                yield client, verification_session
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_child(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/children",
        json={
            "child_name": "Maria Silva",
            "birth_date": "2021-05-10",
            "guardian_name": "Ana Silva",
            "guardian_phone": "82999999999",
            "relationship": "Mother",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert "family_id" in body
    assert "child_id" in body
    assert "guardian_id" in body

    child_id = UUID(body["child_id"])
    family_id = UUID(body["family_id"])
    guardian_id = UUID(body["guardian_id"])

    child = verification_session.get(ChildModel, child_id)
    family = verification_session.get(FamilyModel, family_id)
    guardian = verification_session.get(GuardianModel, guardian_id)

    assert child is not None
    assert child.full_name == "Maria Silva"
    assert child.birth_date == date(2021, 5, 10)

    assert family is not None

    assert guardian is not None
    assert guardian.full_name == "Ana Silva"
    assert guardian.phone == "82999999999"


def test_create_service(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/services",
        json={
            "name": "Sunday Service",
            "starts_at": "2026-10-04T19:00:00",
            "ends_at": "2026-10-04T21:00:00",
        },
    )

    assert response.status_code == 201

    service_id = UUID(response.json()["service_id"])
    service = verification_session.get(ServiceModel, service_id)

    assert service is not None
    assert service.name == "Sunday Service"
    assert service.starts_at == datetime(2026, 10, 4, 19, 0)
    assert service.ends_at == datetime(2026, 10, 4, 21, 0)


def test_create_room(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/rooms",
        json={"name": "Sala Infantil"},
    )

    assert response.status_code == 201

    room_id = UUID(response.json()["room_id"])
    room = verification_session.get(RoomModel, room_id)

    assert room is not None
    assert room.name == "Sala Infantil"
    assert room.is_active is True


def test_list_rooms_returns_only_active_rooms(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    active_room_id = uuid4()

    verification_session.add_all(
        [
            RoomModel(
                id=active_room_id,
                name="Sala Infantil",
                normalized_name="sala infantil",
                is_active=True,
            ),
            RoomModel(
                id=uuid4(),
                name="Sala Desativada",
                normalized_name="sala desativada",
                is_active=False,
            ),
                    ]
    )
    verification_session.commit()

    response = client.get("/api/rooms")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(active_room_id),
            "name": "Sala Infantil",
        }
    ]


def test_create_session(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()
    room_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 11, 19, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        "/api/sessions",
        json={
            "service_id": str(service_id),
            "room_id": str(room_id),
            "name": "Infantil",
            "min_age_years": 3,
            "max_age_years": 5,
        },
    )

    assert response.status_code == 201

    session_id = UUID(response.json()["session_id"])

    created_session = verification_session.get(
        SessionModel,
        session_id,
    )

    assert created_session is not None
    assert created_session.service_id == service_id
    assert created_session.room_id == room_id
    assert created_session.name == "Infantil"
    assert created_session.min_age_years == 3
    assert created_session.max_age_years == 5
    assert created_session.status == "scheduled"


def test_create_session_returns_404_when_service_not_found(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/sessions",
        json={
            "service_id": str(uuid4()),
            "room_id": str(uuid4()),
            "name": "Infantil",
            "min_age_years": 3,
            "max_age_years": 5,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service not found",
    }

    assert verification_session.query(SessionModel).count() == 0


def test_create_session_returns_404_when_room_not_found(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()

    verification_session.add(
        ServiceModel(
            id=service_id,
            name="Sunday Service",
            starts_at=datetime(2026, 10, 11, 19, 0),
            ends_at=None,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/sessions",
        json={
            "service_id": str(service_id),
            "room_id": str(uuid4()),
            "name": "Infantil",
            "min_age_years": 3,
            "max_age_years": 5,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Room not found",
    }

    assert verification_session.query(SessionModel).count() == 0


def test_create_session_returns_409_when_room_is_inactive(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()
    room_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 11, 19, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=False,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        "/api/sessions",
        json={
            "service_id": str(service_id),
            "room_id": str(room_id),
            "name": "Infantil",
            "min_age_years": 3,
            "max_age_years": 5,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Room is inactive",
    }

    assert verification_session.query(SessionModel).count() == 0


def test_create_session_returns_409_when_room_already_assigned(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()
    room_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 11, 19, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    payload = {
        "service_id": str(service_id),
        "room_id": str(room_id),
        "name": "Infantil",
        "min_age_years": 3,
        "max_age_years": 5,
    }

    first_response = client.post(
        "/api/sessions",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/sessions",
        json={
            **payload,
            "name": "Outra Turma",
            "min_age_years": 6,
            "max_age_years": 11,
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Room already assigned to this service",
    }

    persisted_sessions = (
        verification_session.query(SessionModel)
        .filter(SessionModel.service_id == service_id)
        .all()
    )

    assert len(persisted_sessions) == 1
    assert persisted_sessions[0].room_id == room_id
    assert persisted_sessions[0].name == "Infantil"


def test_create_session_returns_422_for_invalid_age_range(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()
    room_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 11, 19, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        "/api/sessions",
        json={
            "service_id": str(service_id),
            "room_id": str(room_id),
            "name": "Infantil",
            "min_age_years": 11,
            "max_age_years": 3,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Invalid age range",
    }

    assert verification_session.query(SessionModel).count() == 0


def test_create_room_returns_409_for_duplicate_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    first_response = client.post(
        "/api/rooms",
        json={"name": "Sala Infantil"},
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/rooms",
        json={"name": "  sala   infantil  "},
    )

    assert duplicate_response.status_code == 409

    rooms = verification_session.query(RoomModel).all()

    assert len(rooms) == 1
    assert rooms[0].name == "Sala Infantil"


def test_check_in_child_creates_attendance(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": occurred_at.isoformat(),
        },
    )

    assert response.status_code == 201

    attendance_id = UUID(response.json()["attendance_id"])

    attendance = verification_session.get(
        AttendanceModel,
        attendance_id,
    )

    assert attendance is not None
    assert attendance.child_id == child_id
    assert attendance.session_id == session_id
    assert attendance.checked_in_at == occurred_at
    assert attendance.checked_out_at is None


def test_check_in_child_returns_404_when_child_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(uuid4()),
            "session_id": str(uuid4()),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child not found",
    }

    assert verification_session.query(AttendanceModel).count() == 0


def test_check_in_child_returns_404_when_session_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    family_id = uuid4()
    child_id = uuid4()

    verification_session.add(
        FamilyModel(
            id=family_id,
            is_active=True,
        )
    )
    verification_session.flush()

    verification_session.add(
        ChildModel(
            id=child_id,
            family_id=family_id,
            full_name="Maria Silva",
            birth_date=date(2021, 5, 10),
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(uuid4()),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Session not found",
    }

    assert verification_session.query(AttendanceModel).count() == 0


def test_check_in_child_returns_409_when_already_checked_in(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    payload = {
        "child_id": str(child_id),
        "session_id": str(session_id),
        "occurred_at": "2026-10-17T10:00:00",
    }

    first_response = client.post("/api/check-ins", json=payload)

    assert first_response.status_code == 201

    second_response = client.post("/api/check-ins", json=payload)

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Child already checked in",
    }

    assert verification_session.query(AttendanceModel).count() == 1


def test_check_in_child_returns_409_when_session_is_closed(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
        session_status="closed",
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": occurred_at.isoformat(),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Session is not open",
    }
    assert verification_session.query(AttendanceModel).count() == 0


def test_check_in_child_returns_409_when_child_is_inactive(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
        child_is_active=False,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": occurred_at.isoformat(),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Child is inactive",
    }
    assert verification_session.query(AttendanceModel).count() == 0


def test_check_in_child_returns_409_when_family_is_inactive(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
        family_is_active=False,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": occurred_at.isoformat(),
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Family is inactive",
    }
    assert verification_session.query(AttendanceModel).count() == 0


def test_check_in_child_returns_422_when_child_age_is_out_of_range(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
        child_birth_date=date(2015, 5, 10),
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": occurred_at.isoformat(),
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Child age is out of range",
    }
    assert verification_session.query(AttendanceModel).count() == 0


def test_check_out_child_updates_attendance(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert check_in_response.status_code == 201

    attendance_id = UUID(check_in_response.json()["attendance_id"])

    response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(attendance_id),
            "guardian_id": str(guardian_id),
            "occurred_at": "2026-10-17T11:00:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "attendance_id": str(attendance_id),
    }

    verification_session.expire_all()

    attendance = verification_session.get(
        AttendanceModel,
        attendance_id,
    )

    assert attendance is not None
    assert attendance.checked_in_at == datetime(2026, 10, 17, 10, 0)
    assert attendance.checked_out_at == datetime(2026, 10, 17, 11, 0)
    assert attendance.checked_out_by_guardian_id == guardian_id


def test_check_out_child_returns_403_for_unauthorized_guardian(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    check_in_response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert check_in_response.status_code == 201
    attendance_id = UUID(check_in_response.json()["attendance_id"])

    # This guardian has no authorization to pick up the child.
    response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(attendance_id),
            "guardian_id": str(uuid4()),
            "occurred_at": "2026-10-17T11:00:00",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Guardian is not authorized to pick up this child",
    }

    verification_session.expire_all()

    attendance = verification_session.get(
        AttendanceModel,
        attendance_id,
    )

    assert attendance is not None
    assert attendance.checked_out_at is None
    assert attendance.checked_out_by_guardian_id is None


def test_check_out_child_returns_404_when_attendance_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(uuid4()),
            "guardian_id": str(uuid4()),
            "occurred_at": "2026-10-17T11:00:00",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Attendance not found",
    }

    assert verification_session.query(AttendanceModel).count() == 0


def test_check_out_child_returns_409_when_already_checked_out(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert check_in_response.status_code == 201
    attendance_id = UUID(check_in_response.json()["attendance_id"])

    first_response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(attendance_id),
            "occurred_at": "2026-10-17T11:00:00",
            "guardian_id": str(guardian_id),
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(attendance_id),
            "occurred_at": "2026-10-17T11:30:00",
            "guardian_id": str(guardian_id),
        },
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Attendance already checked out",
    }

    verification_session.expire_all()

    attendance = verification_session.get(
        AttendanceModel,
        attendance_id,
    )

    assert attendance is not None
    assert attendance.checked_out_at == datetime(2026, 10, 17, 11, 0)
    assert verification_session.query(AttendanceModel).count() == 1


def test_check_out_child_returns_422_when_checkout_precedes_checkin(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": "2026-10-17T10:00:00",
        },
    )

    assert check_in_response.status_code == 201
    attendance_id = UUID(check_in_response.json()["attendance_id"])

    response = client.post(
        "/api/check-outs",
        json={
            "attendance_id": str(attendance_id),
            "guardian_id": str(guardian_id),
            "occurred_at": "2026-10-17T09:30:00",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Check-out cannot occur before check-in",
    }

    verification_session.expire_all()

    attendance = verification_session.get(
        AttendanceModel,
        attendance_id,
    )

    assert attendance is not None
    assert attendance.checked_out_at is None
    assert verification_session.query(AttendanceModel).count() == 1
