from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import (
    get_db_session,
    get_jwt_token_service,
)
from church_city_kids.api.main import app
from church_city_kids.domain.people import Family, Guardian
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
    MinistrySettingsModel,
    RoomModel,
    ServiceModel,
    SessionModel,
    UserModel,
    VolunteerAssignmentModel,
    VolunteerModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    FamilyRepository,
    GuardianRepository,
)
from church_city_kids.infrastructure.security.jwt_tokens import (
    JwtTokenService,
)
from church_city_kids.infrastructure.security.passwords import (
    PasswordHasher,
)


def create_authenticated_headers(
    session: Session,
    *,
    role: str = "volunteer",
) -> dict[str, str]:
    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username=f"test-user-{user_id}",
            password_hash="test-hash",
            is_active=True,
            role=role,
        )
    )
    session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(user_id)

    return {"Authorization": f"Bearer {token}"}


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

    app.dependency_overrides[get_jwt_token_service] = lambda: JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

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

    verification_session.add(
        MinistrySettingsModel(
            pager_required=True,
        )
    )
    verification_session.commit()
    headers = create_authenticated_headers(verification_session)

    response = client.post(
        "/api/children",
        headers=headers,
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


def test_list_children_returns_matching_children(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    matching_child_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=matching_child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            ),
            ChildModel(
                id=uuid4(),
                family_id=family_id,
                full_name="João Silva",
                birth_date=date(2020, 3, 15),
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        "/api/children",
        params={"name": "maria"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(matching_child_id),
            "family_id": str(family_id),
            "full_name": "Maria Silva",
            "birth_date": "2021-05-10",
        }
    ]


def test_list_children_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(
        "/api/children",
        params={"name": "maria"},
    )

    assert response.status_code == 401


def test_list_children_returns_empty_list_when_no_matches(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        "/api/children",
        params={"name": "NomeInexistente"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_create_service_creates_sessions_for_active_rooms(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    nursery_id = uuid4()
    children_id = uuid4()
    inactive_id = uuid4()

    verification_session.add_all(
        [
            RoomModel(
                id=nursery_id,
                name="Sala 1",
                normalized_name="sala 1",
                is_active=True,
                min_age_years=3,
                max_age_years=5,
            ),
            RoomModel(
                id=children_id,
                name="Sala 2",
                normalized_name="sala 2",
                is_active=True,
                min_age_years=6,
                max_age_years=11,
            ),
            RoomModel(
                id=inactive_id,
                name="Sala desativada",
                normalized_name="sala desativada",
                is_active=False,
                min_age_years=12,
                max_age_years=14,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        "/api/services",
        headers=headers,
        json={
            "name": "Culto 22/11/2026",
            "starts_at": "2026-11-22T09:00:00",
            "ends_at": "2026-11-22T11:00:00",
        },
    )

    assert response.status_code == 201

    service_id = UUID(response.json()["service_id"])
    service = verification_session.get(ServiceModel, service_id)

    assert service is not None
    assert service.name == "Culto 22/11/2026"

    sessions = verification_session.scalars(
        select(SessionModel)
        .where(SessionModel.service_id == service_id)
        .order_by(SessionModel.name)
    ).all()

    assert len(sessions) == 2

    sessions_by_room = {session.room_id: session for session in sessions}

    nursery_session = sessions_by_room[nursery_id]
    assert nursery_session.name == "Sala 1"
    assert nursery_session.min_age_years == 3
    assert nursery_session.max_age_years == 5

    children_session = sessions_by_room[children_id]
    assert children_session.name == "Sala 2"
    assert children_session.min_age_years == 6
    assert children_session.max_age_years == 11

    assert inactive_id not in sessions_by_room


def test_create_room(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.post(
        "/api/rooms",
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    verification_session.add_all(
        [
            RoomModel(
                id=active_room_id,
                name="Sala Infantil",
                normalized_name="sala infantil",
                is_active=True,
                min_age_years=3,
                max_age_years=5,
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

    response = client.get(
        "/api/rooms",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "id": str(active_room_id),
            "name": "Sala Infantil",
            "min_age_years": 3,
            "max_age_years": 5,
        }
    ]


def test_create_session(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

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
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.post(
        "/api/sessions",
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )
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
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )
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
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )
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
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/sessions",
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

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
        headers=headers,
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
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    first_response = client.post(
        "/api/rooms",
        headers=headers,
        json={"name": "Sala Infantil"},
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/api/rooms",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

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
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    payload = {
        "child_id": str(child_id),
        "session_id": str(session_id),
        "occurred_at": "2026-10-17T10:00:00",
    }

    first_response = client.post(
        "/api/check-ins",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/check-ins",
        json=payload,
        headers=headers,
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Child already checked in",
    }

    assert verification_session.query(AttendanceModel).count() == 1


def test_check_in_child_returns_409_when_session_is_closed(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
        session_status="closed",
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
        child_is_active=False,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
        family_is_active=False,
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
        child_birth_date=date(2015, 5, 10),
    )
    occurred_at = datetime(2026, 10, 17, 10, 0)

    response = client.post(
        "/api/check-ins",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        headers=headers,
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
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    check_in_response = client.post(
        "/api/check-ins",
        headers=headers,
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
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    response = client.post(
        "/api/check-outs",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        headers=headers,
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
        headers=headers,
        json={
            "attendance_id": str(attendance_id),
            "occurred_at": "2026-10-17T11:00:00",
            "guardian_id": str(guardian_id),
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/check-outs",
        headers=headers,
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
    headers = create_authenticated_headers(verification_session)

    child_id, session_id = create_check_in_scenario(
        verification_session,
    )

    guardian_id = create_authorized_guardian(
        verification_session,
        child_id,
    )

    check_in_response = client.post(
        "/api/check-ins",
        headers=headers,
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
        headers=headers,
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


def test_update_ministry_settings_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
    )

    assert response.status_code == 401


def test_update_ministry_settings_rejects_invalid_token(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.patch(
        "/api/admin/settings",
        headers={
            "Authorization": "Bearer invalid-token",
        },
        json={"pager_required": False},
    )

    assert response.status_code == 401


def test_admin_settings_rejects_token_for_unknown_user(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(uuid4())

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_admin_settings_rejects_authenticated_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    verification_session.add(
        MinistrySettingsModel(
            id=1,
            pager_required=True,
        )
    )
    verification_session.commit()

    user_id = uuid4()

    verification_session.add(
        UserModel(
            id=user_id,
            username="reception.volunteer",
            password_hash="test-hash",
            is_active=True,
            role="volunteer",
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(user_id)

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

    verification_session.expire_all()
    settings = verification_session.get(MinistrySettingsModel, 1)

    assert settings is not None
    assert settings.pager_required is True


def test_admin_settings_returns_404_when_settings_missing(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    user_id = uuid4()

    verification_session.add(
        UserModel(
            id=user_id,
            username="reception.admin",
            password_hash="test-hash",
            is_active=True,
            role="admin",
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(user_id)

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ministry settings not found"


def test_admin_settings_rejects_token_for_inactive_user(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    user_id = uuid4()

    verification_session.add(
        UserModel(
            id=user_id,
            username="inactive.admin",
            password_hash="test-hash",
            is_active=False,
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(user_id)

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid or expired authentication token")


def test_admin_settings_rejects_invalid_jwt_signature(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    token_service = JwtTokenService(
        secret_key="different-test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(uuid4())

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid or expired authentication token")
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_admin_settings_rejects_expired_jwt(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    token = token_service.create_access_token(uuid4())

    payload = jwt.decode(
        token,
        "test-secret-key-with-at-least-32-bytes",
        algorithms=["HS256"],
        options={"verify_exp": False},
    )

    payload["exp"] = datetime(2020, 1, 1, tzinfo=UTC)

    expired_token = jwt.encode(
        payload,
        "test-secret-key-with-at-least-32-bytes",
        algorithm="HS256",
    )

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == ("Invalid or expired authentication token")
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_returns_access_token_for_valid_credentials(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    user_id = uuid4()
    password = "strong-test-password"

    verification_session.add(
        UserModel(
            id=user_id,
            username="reception.admin",
            password_hash=PasswordHasher().hash(password),
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "reception.admin",
            "password": password,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )

    assert token_service.decode_access_token(body["access_token"]) == user_id


def test_login_rejects_incorrect_password(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    verification_session.add(
        UserModel(
            id=uuid4(),
            username="reception.admin",
            password_hash=PasswordHasher().hash("correct-password"),
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "reception.admin",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_rejects_unknown_username(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.post(
        "/api/auth/login",
        json={
            "username": "unknown.user",
            "password": "any-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_rejects_inactive_user(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    password = "correct-password"

    verification_session.add(
        UserModel(
            id=uuid4(),
            username="inactive.admin",
            password_hash=PasswordHasher().hash(password),
            is_active=False,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "inactive.admin",
            "password": password,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_admin_can_update_pager_required(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    verification_session.add(
        MinistrySettingsModel(
            id=1,
            pager_required=True,
        )
    )
    verification_session.commit()

    user_id = uuid4()

    verification_session.add(
        UserModel(
            id=user_id,
            username="settings.admin",
            password_hash="test-hash",
            is_active=True,
            role="admin",
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    token = token_service.create_access_token(user_id)

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    verification_session.expire_all()
    settings = verification_session.get(MinistrySettingsModel, 1)

    assert settings is not None
    assert settings.pager_required is False


def test_admin_settings_rejects_invalid_pager_required(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    verification_session.add(MinistrySettingsModel(id=1, pager_required=True))

    user_id = uuid4()
    verification_session.add(
        UserModel(
            id=user_id,
            username="validation.admin",
            password_hash="test-hash",
            is_active=True,
            role="admin",
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    token = token_service.create_access_token(user_id)

    response = client.patch(
        "/api/admin/settings",
        json={"pager_required": "false"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422

    verification_session.expire_all()
    settings = verification_session.get(MinistrySettingsModel, 1)

    assert settings is not None
    assert settings.pager_required is True


def test_admin_settings_rolls_back_when_commit_fails(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    verification_session.add(MinistrySettingsModel(id=1, pager_required=True))

    user_id = uuid4()
    verification_session.add(
        UserModel(
            id=user_id,
            username="rollback.admin",
            password_hash="test-hash",
            is_active=True,
            role="admin",
        )
    )
    verification_session.commit()

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    token = token_service.create_access_token(user_id)

    with (
        patch.object(Session, "commit", side_effect=RuntimeError("Database error")),
        patch.object(Session, "rollback", autospec=True) as rollback_mock,
    ):
        response = client.patch(
            "/api/admin/settings",
            json={"pager_required": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 500
        rollback_mock.assert_called_once()

    verification_session.expire_all()
    settings = verification_session.get(MinistrySettingsModel, 1)
    assert settings is not None
    assert settings.pager_required is True


def test_check_in_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id, session_id = create_check_in_scenario(verification_session)
    verification_session.commit()

    response = client.post(
        "/api/check-ins",
        json={
            "child_id": str(child_id),
            "session_id": str(session_id),
            "occurred_at": "2026-10-17T09:30:00",
        },
    )

    assert response.status_code == 401


def test_check_out_requires_authentication(
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

    assert response.status_code == 401


def test_register_child_requires_authentication(api_client):
    client, _ = api_client

    response = client.post("/api/children", json={})

    assert response.status_code == 401


def test_create_service_requires_authentication(api_client):
    client, _ = api_client

    response = client.post("/api/services", json={})

    assert response.status_code == 401


def test_create_service_rejects_volunteer(api_client):
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.post(
        "/api/services",
        headers=headers,
        json={},
    )

    assert response.status_code == 403


def test_create_room_requires_authentication(api_client):
    client, _ = api_client
    response = client.post("/api/rooms", json={})
    assert response.status_code == 401


def test_create_room_rejects_volunteer(api_client):
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.post(
        "/api/rooms",
        headers=headers,
        json={},
    )

    assert response.status_code == 403


def test_list_rooms_requires_authentication(api_client):
    client, _ = api_client
    response = client.get("/api/rooms")
    assert response.status_code == 401


def test_create_session_requires_authentication(api_client):
    client, _ = api_client
    response = client.post("/api/sessions", json={})
    assert response.status_code == 401


def test_create_session_rejects_volunteer(api_client):
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.post(
        "/api/sessions",
        headers=headers,
        json={},
    )

    assert response.status_code == 403


def test_get_child_details_returns_child_and_guardians(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Ana Silva",
                phone="82999999999",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        ChildGuardianModel(
            id=uuid4(),
            child_id=child_id,
            guardian_id=guardian_id,
            relationship="Mother",
            authorized_pickup=True,
        )
    )
    verification_session.commit()

    response = client.get(
        f"/api/children/{child_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(child_id),
        "family_id": str(family_id),
        "full_name": "Maria Silva",
        "birth_date": "2021-05-10",
        "guardians": [
            {
                "id": str(guardian_id),
                "full_name": "Ana Silva",
                "phone": "82999999999",
                "relationship": "Mother",
                "authorized_pickup": True,
                "is_active": True,
            }
        ],
    }


def test_get_child_details_returns_404_when_child_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    child_id = uuid4()

    response = client.get(
        f"/api/children/{child_id}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child not found",
    }


def test_get_child_details_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    child_id = uuid4()

    response = client.get(
        f"/api/children/{child_id}",
    )

    assert response.status_code == 401


def test_add_existing_guardian_to_child(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    child_family_id = uuid4()
    guardian_family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    verification_session.add_all(
        [
            FamilyModel(id=child_family_id, is_active=True),
            FamilyModel(id=guardian_family_id, is_active=True),
        ]
    )
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=child_family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=guardian_family_id,
                full_name="Maria Silva",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "guardian_id": str(guardian_id),
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 201

    data = response.json()
    link_id = UUID(data["link_id"])

    link = verification_session.get(ChildGuardianModel, link_id)

    assert link is not None
    assert link.child_id == child_id
    assert link.guardian_id == guardian_id
    assert link.relationship == "Grandmother"
    assert link.authorized_pickup is True


def test_add_child_guardian_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    child_id = uuid4()
    guardian_id = uuid4()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        json={
            "guardian_id": str(guardian_id),
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 401
    assert verification_session.query(ChildGuardianModel).count() == 0


def test_add_child_guardian_returns_409_for_duplicate_link(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()
    existing_link_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Maria Silva",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        ChildGuardianModel(
            id=existing_link_id,
            child_id=child_id,
            guardian_id=guardian_id,
            relationship="Mother",
            authorized_pickup=False,
        )
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "guardian_id": str(guardian_id),
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Guardian already linked to child",
    }

    verification_session.expire_all()

    links = verification_session.scalars(select(ChildGuardianModel)).all()

    assert len(links) == 1
    assert links[0].id == existing_link_id
    assert links[0].relationship == "Mother"
    assert links[0].authorized_pickup is False


def test_add_child_guardian_returns_404_when_child_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.post(
        f"/api/children/{uuid4()}/guardians",
        headers=headers,
        json={
            "guardian_id": str(uuid4()),
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child not found",
    }

    assert (
        verification_session.scalar(
            select(func.count()).select_from(ChildGuardianModel)
        )
        == 0
    )


def test_add_child_guardian_returns_404_when_guardian_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add(
        ChildModel(
            id=child_id,
            family_id=family_id,
            full_name="Test Child",
            birth_date=date(2021, 1, 1),
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "guardian_id": str(uuid4()),
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Guardian not found",
    }

    assert (
        verification_session.scalar(
            select(func.count()).select_from(ChildGuardianModel)
        )
        == 0
    )


def test_add_child_guardian_defaults_to_unauthorized_pickup(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Maria Silva",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "guardian_id": str(guardian_id),
            "relationship": "Grandmother",
        },
    )

    assert response.status_code == 201

    link_id = UUID(response.json()["link_id"])

    verification_session.expire_all()
    link = verification_session.get(ChildGuardianModel, link_id)

    assert link is not None
    assert link.authorized_pickup is False
    assert link.relationship == "Grandmother"


def test_add_new_guardian_to_existing_child_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add(
        ChildModel(
            id=child_id,
            family_id=family_id,
            full_name="Test Child",
            birth_date=date(2021, 1, 1),
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "full_name": "Ana Silva",
            "phone": "82999999999",
            "relationship": "Grandmother",
        },
    )

    assert response.status_code == 201

    link_id = UUID(response.json()["link_id"])

    verification_session.expire_all()

    link = verification_session.get(ChildGuardianModel, link_id)
    assert link is not None

    guardian = verification_session.get(
        GuardianModel,
        link.guardian_id,
    )
    assert guardian is not None
    assert guardian.family_id == family_id
    assert guardian.full_name == "Ana Silva"
    assert guardian.phone == "82999999999"

    assert link.child_id == child_id
    assert link.relationship == "Grandmother"
    assert link.authorized_pickup is False

    assert (
        verification_session.scalar(select(func.count()).select_from(FamilyModel)) == 1
    )

    assert (
        verification_session.scalar(select(func.count()).select_from(ChildModel)) == 1
    )


def test_add_child_guardian_rejects_ambiguous_input(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Existing Guardian",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.post(
        f"/api/children/{child_id}/guardians",
        headers=headers,
        json={
            "guardian_id": str(guardian_id),
            "full_name": "New Guardian",
            "relationship": "Grandmother",
        },
    )

    assert response.status_code == 422

    verification_session.expire_all()

    assert (
        verification_session.scalar(
            select(func.count()).select_from(ChildGuardianModel)
        )
        == 0
    )

    assert (
        verification_session.scalar(select(func.count()).select_from(GuardianModel))
        == 1
    )


def test_add_child_guardian_rejects_missing_guardian_input(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.post(
        f"/api/children/{uuid4()}/guardians",
        headers=headers,
        json={
            "relationship": "Grandmother",
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 422

    assert (
        verification_session.scalar(select(func.count()).select_from(GuardianModel))
        == 0
    )

    assert (
        verification_session.scalar(
            select(func.count()).select_from(ChildGuardianModel)
        )
        == 0
    )


def test_update_child_guardian_pickup_authorization_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()
    link_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Existing Guardian",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        ChildGuardianModel(
            id=link_id,
            child_id=child_id,
            guardian_id=guardian_id,
            relationship="Uncle",
            authorized_pickup=False,
        )
    )
    verification_session.commit()

    response = client.patch(
        f"/api/children/{child_id}/guardians/{guardian_id}",
        headers=headers,
        json={
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 200

    verification_session.expire_all()

    link = verification_session.get(
        ChildGuardianModel,
        link_id,
    )

    assert link is not None
    assert link.relationship == "Uncle"
    assert link.authorized_pickup is True


def test_update_child_guardian_clears_relationship_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()
    link_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Existing Guardian",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        ChildGuardianModel(
            id=link_id,
            child_id=child_id,
            guardian_id=guardian_id,
            relationship="Uncle",
            authorized_pickup=True,
        )
    )
    verification_session.commit()

    response = client.patch(
        f"/api/children/{child_id}/guardians/{guardian_id}",
        headers=headers,
        json={
            "relationship": None,
        },
    )

    assert response.status_code == 200

    verification_session.expire_all()

    link = verification_session.get(
        ChildGuardianModel,
        link_id,
    )

    assert link is not None
    assert link.relationship is None
    assert link.authorized_pickup is True


def test_update_child_guardian_returns_404_for_missing_link(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.patch(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
        headers=headers,
        json={
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child guardian link not found",
    }


def test_update_child_guardian_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.patch(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
        json={
            "authorized_pickup": True,
        },
    )

    assert response.status_code == 401


def test_update_child_guardian_rejects_null_pickup_authorization(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.patch(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
        headers=headers,
        json={
            "authorized_pickup": None,
        },
    )

    assert response.status_code == 422


def test_update_child_guardian_rejects_empty_patch(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.patch(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_delete_child_guardian_returns_204(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    family = FamilyModel(
        id=uuid4(),
        is_active=True,
    )
    verification_session.add(family)
    verification_session.flush()

    child = ChildModel(
        id=uuid4(),
        family_id=family.id,
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
        is_active=True,
    )

    guardian = GuardianModel(
        id=uuid4(),
        family_id=family.id,
        full_name="João Silva",
        is_active=True,
    )

    verification_session.add_all([child, guardian])
    verification_session.flush()

    link = ChildGuardianModel(
        id=uuid4(),
        child_id=child.id,
        guardian_id=guardian.id,
        relationship="Uncle",
        authorized_pickup=True,
    )

    verification_session.add(link)
    verification_session.commit()

    link_id = link.id
    child_id = child.id
    guardian_id = guardian.id

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.delete(
        f"/api/children/{child.id}/guardians/{guardian.id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    verification_session.expire_all()

    assert verification_session.get(ChildGuardianModel, link_id) is None
    assert verification_session.get(ChildModel, child_id) is not None
    assert verification_session.get(GuardianModel, guardian_id) is not None


def test_delete_nonexistent_child_guardian_returns_404(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.delete(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child guardian link not found",
    }


def test_delete_child_guardian_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.delete(
        f"/api/children/{uuid4()}/guardians/{uuid4()}",
    )

    assert response.status_code == 401


def test_get_child_attendance_history_returns_empty_list(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

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

    response = client.get(
        f"/api/children/{child_id}/attendance",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_child_attendance_history_returns_404_when_child_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    child_id = uuid4()

    response = client.get(
        f"/api/children/{child_id}/attendance",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Child not found",
    }


def test_get_child_attendance_history_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    child_id = uuid4()

    response = client.get(
        f"/api/children/{child_id}/attendance",
    )

    assert response.status_code == 401


def test_get_child_attendance_history_returns_attendance_details(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()

    service_starts_at = datetime(2026, 10, 25, 9, 0)
    checked_in_at = datetime(2026, 10, 25, 9, 10)
    checked_out_at = datetime(2026, 10, 25, 11, 0)

    verification_session.add(
        FamilyModel(
            id=family_id,
            is_active=True,
        )
    )
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Ana Silva",
                phone="82999999999",
                is_active=True,
            ),
            ServiceModel(
                id=service_id,
                name="Sunday Morning",
                starts_at=service_starts_at,
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Kids 4-6",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        SessionModel(
            id=session_id,
            service_id=service_id,
            room_id=room_id,
            name="Kids 4-6",
            min_age_years=4,
            max_age_years=6,
            status="CLOSED",
        )
    )
    verification_session.flush()

    verification_session.add(
        AttendanceModel(
            id=attendance_id,
            child_id=child_id,
            session_id=session_id,
            checked_in_at=checked_in_at,
            checked_out_at=checked_out_at,
            checked_out_by_guardian_id=guardian_id,
        )
    )
    verification_session.commit()

    response = client.get(
        f"/api/children/{child_id}/attendance",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "attendance_id": str(attendance_id),
            "child_id": str(child_id),
            "service_name": "Sunday Morning",
            "service_starts_at": "2026-10-25T09:00:00",
            "room_name": "Kids 4-6",
            "checked_in_at": "2026-10-25T09:10:00",
            "checked_out_at": "2026-10-25T11:00:00",
            "checked_out_by_guardian_name": "Ana Silva",
        }
    ]


def test_list_service_attendances_returns_present_children(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()

    checked_in_at = datetime(2026, 10, 25, 9, 10)

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            ),
            ServiceModel(
                id=service_id,
                name="Sunday Morning",
                starts_at=datetime(2026, 10, 25, 9, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Kids 4-6",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add(
        SessionModel(
            id=session_id,
            service_id=service_id,
            room_id=room_id,
            name="Kids 4-6 Morning",
            min_age_years=4,
            max_age_years=6,
            status="OPEN",
        )
    )
    verification_session.flush()

    verification_session.add(
        AttendanceModel(
            id=attendance_id,
            child_id=child_id,
            session_id=session_id,
            checked_in_at=checked_in_at,
            checked_out_at=None,
            checked_out_by_guardian_id=None,
        )
    )
    verification_session.commit()

    response = client.get(
        f"/api/services/{service_id}/attendances",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "attendance_id": str(attendance_id),
            "service_id": str(service_id),
            "child_id": str(child_id),
            "child_name": "Maria Silva",
            "room_id": str(room_id),
            "room_name": "Kids 4-6",
            "checked_in_at": checked_in_at.isoformat(),
            "checked_out_at": None,
        }
    ]


def test_list_service_attendances_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(
        f"/api/services/{uuid4()}/attendances",
    )

    assert response.status_code == 401


def test_list_service_attendances_returns_empty_list_for_service_without_attendances(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    service_id = uuid4()

    verification_session.add(
        ServiceModel(
            id=service_id,
            name="Sunday Morning",
            starts_at=datetime(2026, 10, 25, 9, 0),
            ends_at=None,
        )
    )
    verification_session.commit()

    response = client.get(
        f"/api/services/{service_id}/attendances",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_service_attendances_returns_404_when_service_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    nonexistent_service_id = uuid4()

    response = client.get(
        f"/api/services/{nonexistent_service_id}/attendances",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Service not found",
    }


def test_list_families_returns_family_matching_child_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

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

    response = client.get(
        "/api/families",
        params={"name": "mArIa"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(family_id),
            "is_active": True,
        }
    ]


def test_list_families_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(
        "/api/families",
        params={"name": "maria"},
    )

    assert response.status_code == 401


def test_list_families_returns_family_matching_guardian_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(
        FamilyModel(
            id=family_id,
            is_active=True,
        )
    )
    verification_session.flush()

    verification_session.add(
        GuardianModel(
            id=guardian_id,
            family_id=family_id,
            full_name="João Oliveira",
            phone="82999999999",
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.get(
        "/api/families",
        params={"name": "oLiVeIrA"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(family_id),
            "is_active": True,
        }
    ]


def test_list_families_returns_empty_list_when_no_matches(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        "/api/families",
        params={"name": "inexistente"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_family_details_returns_children_and_guardians(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Maria Silva",
                birth_date=date(2021, 5, 10),
                is_active=True,
            ),
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="João Silva",
                phone="82999999999",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        f"/api/families/{family_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(family_id),
        "is_active": True,
        "children": [
            {
                "id": str(child_id),
                "full_name": "Maria Silva",
                "birth_date": "2021-05-10",
                "is_active": True,
            }
        ],
        "guardians": [
            {
                "id": str(guardian_id),
                "full_name": "João Silva",
                "phone": "82999999999",
                "is_active": True,
            }
        ],
    }


def test_get_family_details_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(f"/api/families/{uuid4()}")

    assert response.status_code == 401


def test_get_family_details_returns_404_for_unknown_family(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        f"/api/families/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Family not found"}


def test_get_family_details_returns_empty_members_for_empty_family(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.commit()

    response = client.get(
        f"/api/families/{family_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(family_id),
        "is_active": True,
        "children": [],
        "guardians": [],
    }


def test_list_guardians_returns_matching_guardians(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add_all(
        [
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Maria Oliveira",
                phone="82999999999",
                is_active=True,
            ),
            GuardianModel(
                id=uuid4(),
                family_id=family_id,
                full_name="João Silva",
                is_active=True,
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        "/api/guardians",
        params={"name": "mArIa"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(guardian_id),
            "family_id": str(family_id),
            "full_name": "Maria Oliveira",
            "phone": "82999999999",
            "is_active": True,
        }
    ]


def test_list_guardians_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(
        "/api/guardians",
        params={"name": "Maria"},
    )

    assert response.status_code == 401


def test_list_guardians_returns_empty_list_when_no_matches(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        "/api/guardians",
        params={"name": "Nonexistent Guardian"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_guardians_requires_name_parameter(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        "/api/guardians",
        headers=headers,
    )

    assert response.status_code == 422


def test_get_guardian_details_returns_children_across_families(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    guardian_family_id = uuid4()
    other_family_id = uuid4()
    guardian_id = uuid4()
    first_child_id = uuid4()
    second_child_id = uuid4()

    verification_session.add_all(
        [
            FamilyModel(id=guardian_family_id, is_active=True),
            FamilyModel(id=other_family_id, is_active=True),
        ]
    )
    verification_session.flush()

    verification_session.add_all(
        [
            GuardianModel(
                id=guardian_id,
                family_id=guardian_family_id,
                full_name="Maria Oliveira",
                phone="82999999999",
                is_active=True,
            ),
            ChildModel(
                id=first_child_id,
                family_id=guardian_family_id,
                full_name="Ana Oliveira",
                birth_date=date(2020, 5, 10),
                is_active=True,
            ),
            ChildModel(
                id=second_child_id,
                family_id=other_family_id,
                full_name="Pedro Silva",
                birth_date=date(2021, 8, 15),
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add_all(
        [
            ChildGuardianModel(
                id=uuid4(),
                child_id=first_child_id,
                guardian_id=guardian_id,
                relationship="Mother",
                authorized_pickup=True,
            ),
            ChildGuardianModel(
                id=uuid4(),
                child_id=second_child_id,
                guardian_id=guardian_id,
                relationship="Aunt",
                authorized_pickup=False,
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        f"/api/guardians/{guardian_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(guardian_id),
        "family_id": str(guardian_family_id),
        "full_name": "Maria Oliveira",
        "phone": "82999999999",
        "is_active": True,
        "children": [
            {
                "id": str(first_child_id),
                "family_id": str(guardian_family_id),
                "full_name": "Ana Oliveira",
                "birth_date": "2020-05-10",
                "is_active": True,
                "relationship": "Mother",
                "authorized_pickup": True,
            },
            {
                "id": str(second_child_id),
                "family_id": str(other_family_id),
                "full_name": "Pedro Silva",
                "birth_date": "2021-08-15",
                "is_active": True,
                "relationship": "Aunt",
                "authorized_pickup": False,
            },
        ],
    }


def test_get_guardian_details_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(f"/api/guardians/{uuid4()}")

    assert response.status_code == 401


def test_get_guardian_details_returns_404_for_unknown_guardian(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        f"/api/guardians/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Guardian not found",
    }


def test_get_guardian_details_returns_empty_children_when_unlinked(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    family_id = uuid4()
    guardian_id = uuid4()

    verification_session.add(FamilyModel(id=family_id, is_active=True))
    verification_session.flush()

    verification_session.add(
        GuardianModel(
            id=guardian_id,
            family_id=family_id,
            full_name="João Oliveira",
            phone="82999999999",
            is_active=True,
        )
    )
    verification_session.commit()

    response = client.get(
        f"/api/guardians/{guardian_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(guardian_id),
        "family_id": str(family_id),
        "full_name": "João Oliveira",
        "phone": "82999999999",
        "is_active": True,
        "children": [],
    }


def test_update_child_name_via_api(
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

    headers = create_authenticated_headers(verification_session)

    response = client.patch(
        f"/api/children/{child_id}",
        headers=headers,
        json={"full_name": "Maria Oliveira"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    # Refresh the ORM object to read the committed database state.
    verification_session.expire_all()

    saved_child = verification_session.get(ChildModel, child_id)

    assert saved_child is not None
    assert saved_child.full_name == "Maria Oliveira"
    assert saved_child.birth_date == date(2021, 5, 10)
    assert saved_child.family_id == family_id
    assert saved_child.is_active is True


def test_update_child_requires_authentication(
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

    response = client.patch(
        f"/api/children/{child_id}",
        json={"full_name": "Maria Oliveira"},
    )

    assert response.status_code == 401

    verification_session.expire_all()
    saved_child = verification_session.get(ChildModel, child_id)

    assert saved_child is not None
    assert saved_child.full_name == "Maria Silva"


def test_update_child_returns_404_when_child_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(verification_session)
    nonexistent_child_id = uuid4()

    response = client.patch(
        f"/api/children/{nonexistent_child_id}",
        headers=headers,
        json={"full_name": "Maria Oliveira"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Child not found"}

    assert verification_session.get(ChildModel, nonexistent_child_id) is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"full_name": ""},
        {"full_name": "   "},
        {"full_name": None},
        {"birth_date": None},
        {"birth_date": "not-a-date"},
    ],
)
def test_update_child_rejects_invalid_payload(
    api_client: tuple[TestClient, Session],
    payload: dict[str, object],
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

    headers = create_authenticated_headers(verification_session)

    response = client.patch(
        f"/api/children/{child_id}",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422

    verification_session.expire_all()
    saved_child = verification_session.get(ChildModel, child_id)

    assert saved_child is not None
    assert saved_child.full_name == "Maria Silva"
    assert saved_child.birth_date == date(2021, 5, 10)
    assert saved_child.family_id == family_id
    assert saved_child.is_active is True


def test_update_child_birth_date_via_api(
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

    headers = create_authenticated_headers(verification_session)

    response = client.patch(
        f"/api/children/{child_id}",
        headers=headers,
        json={"birth_date": "2020-08-15"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    verification_session.expire_all()
    saved_child = verification_session.get(ChildModel, child_id)

    assert saved_child is not None
    assert saved_child.birth_date == date(2020, 8, 15)
    assert saved_child.full_name == "Maria Silva"
    assert saved_child.family_id == family_id
    assert saved_child.is_active is True


def test_update_guardian_changes_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family()
    guardian = Guardian(
        family_id=family.id,
        full_name="Ana Silva",
        phone="82999999999",
    )

    FamilyRepository(session).add(family)
    session.flush()
    GuardianRepository(session).add(guardian)
    session.commit()

    headers = create_authenticated_headers(session)

    response = client.patch(
        f"/api/guardians/{guardian.id}",
        json={"full_name": "Ana Oliveira"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    session.expire_all()
    saved_guardian = GuardianRepository(session).get(guardian.id)

    assert saved_guardian is not None
    assert saved_guardian.full_name == "Ana Oliveira"
    assert saved_guardian.phone == "82999999999"
    assert saved_guardian.family_id == family.id
    assert saved_guardian.is_active is True


def test_update_guardian_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family()
    guardian = Guardian(
        family_id=family.id,
        full_name="Ana Silva",
        phone="82999999999",
    )

    FamilyRepository(session).add(family)
    session.flush()
    GuardianRepository(session).add(guardian)
    session.commit()

    response = client.patch(
        f"/api/guardians/{guardian.id}",
        json={"full_name": "Ana Oliveira"},
    )

    assert response.status_code == 401

    session.expire_all()
    saved_guardian = GuardianRepository(session).get(guardian.id)

    assert saved_guardian is not None
    assert saved_guardian.full_name == "Ana Silva"


def test_update_guardian_returns_404_when_guardian_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session)
    nonexistent_guardian_id = uuid4()

    response = client.patch(
        f"/api/guardians/{nonexistent_guardian_id}",
        json={"full_name": "Ana Oliveira"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Guardian not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"full_name": ""},
        {"full_name": "   "},
        {"full_name": None},
        {"full_name": 123},
        {"phone": 123},
    ],
)
def test_update_guardian_rejects_invalid_payload(
    api_client: tuple[TestClient, Session],
    payload: dict[str, object],
) -> None:
    client, session = api_client

    family = Family()
    guardian = Guardian(
        family_id=family.id,
        full_name="Ana Silva",
        phone="82999999999",
    )

    FamilyRepository(session).add(family)
    session.flush()
    GuardianRepository(session).add(guardian)
    session.commit()

    headers = create_authenticated_headers(session)

    response = client.patch(
        f"/api/guardians/{guardian.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()
    saved_guardian = GuardianRepository(session).get(guardian.id)

    assert saved_guardian is not None
    assert saved_guardian.full_name == "Ana Silva"
    assert saved_guardian.phone == "82999999999"


def test_update_guardian_can_remove_phone(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family()
    guardian = Guardian(
        family_id=family.id,
        full_name="Ana Silva",
        phone="82999999999",
    )

    FamilyRepository(session).add(family)
    session.flush()
    GuardianRepository(session).add(guardian)
    session.commit()

    headers = create_authenticated_headers(session)

    response = client.patch(
        f"/api/guardians/{guardian.id}",
        json={"phone": None},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    session.expire_all()
    saved_guardian = GuardianRepository(session).get(guardian.id)

    assert saved_guardian is not None
    assert saved_guardian.phone is None
    assert saved_guardian.full_name == "Ana Silva"
    assert saved_guardian.family_id == family.id
    assert saved_guardian.is_active is True


def test_update_family_admin_can_deactivate_family(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family(is_active=True)
    FamilyRepository(session).add(family)
    session.commit()

    headers = create_authenticated_headers(session, role="admin")

    response = client.patch(
        f"/api/families/{family.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    session.expire_all()
    saved_family = FamilyRepository(session).get(family.id)

    assert saved_family is not None
    assert saved_family.is_active is False


def test_update_family_admin_can_reactivate_family(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family(is_active=False)
    FamilyRepository(session).add(family)
    session.commit()

    headers = create_authenticated_headers(session, role="admin")

    response = client.patch(
        f"/api/families/{family.id}",
        json={"is_active": True},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    session.expire_all()
    saved_family = FamilyRepository(session).get(family.id)

    assert saved_family is not None
    assert saved_family.id == family.id
    assert saved_family.is_active is True


def test_update_family_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family(is_active=True)
    FamilyRepository(session).add(family)
    session.commit()

    response = client.patch(
        f"/api/families/{family.id}",
        json={"is_active": False},
    )

    assert response.status_code == 401

    session.expire_all()
    saved_family = FamilyRepository(session).get(family.id)

    assert saved_family is not None
    assert saved_family.is_active is True


def test_update_family_forbids_volunteers(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    family = Family(is_active=True)
    FamilyRepository(session).add(family)
    session.commit()

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.patch(
        f"/api/families/{family.id}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 403

    session.expire_all()
    saved_family = FamilyRepository(session).get(family.id)

    assert saved_family is not None
    assert saved_family.is_active is True


def test_update_family_returns_404_when_family_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    response = client.patch(
        f"/api/families/{uuid4()}",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Family not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"is_active": None},
        {"is_active": "invalid"},
        {"is_active": 2},
        {"is_active": []},
    ],
)
def test_update_family_rejects_invalid_payload(
    api_client: tuple[TestClient, Session],
    payload: dict[str, object],
) -> None:
    client, session = api_client

    family = Family(is_active=True)
    FamilyRepository(session).add(family)
    session.commit()

    headers = create_authenticated_headers(session, role="admin")

    response = client.patch(
        f"/api/families/{family.id}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()
    saved_family = FamilyRepository(session).get(family.id)

    assert saved_family is not None
    assert saved_family.is_active is True


def test_create_user_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    response = client.post(
        "/api/users",
        json={
            "username": "volunteer.maria",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 401

    saved_user = session.query(UserModel).filter_by(username="volunteer.maria").first()

    assert saved_user is None


def test_volunteer_cannot_create_user(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.post(
        "/api/users",
        json={
            "username": "volunteer.maria",
            "password": "SecurePassword123!",
        },
        headers=headers,
    )

    assert response.status_code == 403

    saved_user = session.query(UserModel).filter_by(username="volunteer.maria").first()

    assert saved_user is None


def test_create_user_rejects_duplicate_username(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    existing_user_id = uuid4()

    session.add(
        UserModel(
            id=existing_user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.post(
        "/api/users",
        json={
            "username": "VOLUNTEER.MARIA",
            "password": "AnotherSecurePassword123!",
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"

    users = session.scalars(
        select(UserModel).where(func.lower(UserModel.username) == "volunteer.maria")
    ).all()

    assert len(users) == 1
    assert users[0].id == existing_user_id


@pytest.mark.parametrize(
    "username,password,expected_detail",
    [
        (
            "   ",
            "SecurePassword123!",
            "Username cannot be blank",
        ),
        (
            "volunteer.maria",
            "short",
            "Password must contain at least 12 characters",
        ),
        (
            "volunteer.maria",
            " " * 12,
            "Password cannot contain only whitespace",
        ),
    ],
)
def test_create_user_rejects_invalid_input(
    api_client: tuple[TestClient, Session],
    username: str,
    password: str,
    expected_detail: str,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    response = client.post(
        "/api/users",
        json={
            "username": username,
            "password": password,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == expected_detail

    users = session.scalars(
        select(UserModel).where(UserModel.username == "volunteer.maria")
    ).all()

    assert users == []


def test_admin_can_deactivate_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == str(user_id)
    assert response_data["is_active"] is False
    assert response_data["username"] == "volunteer.maria"
    assert response_data["role"] == "volunteer"
    assert "password_hash" not in response_data

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is False
    assert saved_user.username == "volunteer.maria"
    assert saved_user.role == "volunteer"


def test_admin_can_reactivate_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=False,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": True},
        headers=headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == str(user_id)
    assert response_data["username"] == "volunteer.maria"
    assert response_data["role"] == "volunteer"
    assert response_data["is_active"] is True
    assert "password_hash" not in response_data

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is True
    assert saved_user.username == "volunteer.maria"
    assert saved_user.password_hash == "existing-hash"
    assert saved_user.role == "volunteer"


def test_update_user_status_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 401

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is True


def test_volunteer_cannot_update_user_status(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 403

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is True


def test_update_user_status_returns_404_when_user_not_found(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    nonexistent_user_id = uuid4()

    response = client.patch(
        f"/api/users/{nonexistent_user_id}/status",
        json={"is_active": False},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

    assert session.get(UserModel, nonexistent_user_id) is None


def test_update_user_status_requires_is_active_field(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={},
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is True


def test_update_user_status_rejects_invalid_is_active(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=True,
            role="volunteer",
        )
    )
    session.commit()

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": "invalid"},
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is True


def test_deactivated_volunteer_cannot_use_existing_token(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    volunteer_headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    admin_headers = create_authenticated_headers(
        session,
        role="admin",
    )

    # Confirm that the volunteer's token initially works.
    response = client.get(
        "/api/families",
        params={"name": "Test"},
        headers=volunteer_headers,
    )

    assert response.status_code == 200, response.json()

    # Locate the volunteer associated with the token.
    volunteer = session.execute(
        select(UserModel).where(
            UserModel.role == "volunteer",
        )
    ).scalar_one()

    # Deactivate the volunteer using the administrative endpoint.
    response = client.patch(
        f"/api/users/{volunteer.id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )

    assert response.status_code == 200

    # The previously issued token must no longer grant access.
    response = client.get(
        "/api/families",
        headers=volunteer_headers,
    )

    assert response.status_code == 401


def test_deactivated_volunteer_cannot_login(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    from church_city_kids.infrastructure.security.passwords import (
        PasswordHasher,
    )

    password = "SecurePassword123!"
    user_id = uuid4()

    session.add(
        UserModel(
            id=user_id,
            username="volunteer.maria",
            password_hash=PasswordHasher().hash(password),
            is_active=False,
            role="volunteer",
        )
    )
    session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "volunteer.maria",
            "password": password,
        },
    )

    assert response.status_code == 401
    assert "access_token" not in response.json()

    session.expire_all()

    saved_user = session.get(UserModel, user_id)

    assert saved_user is not None
    assert saved_user.is_active is False


def test_admin_can_list_users(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    volunteer_id = uuid4()

    session.add(
        UserModel(
            id=volunteer_id,
            username="volunteer.maria",
            password_hash="existing-hash",
            is_active=False,
            role="volunteer",
        )
    )
    session.commit()

    response = client.get(
        "/api/users",
        headers=headers,
    )

    assert response.status_code == 200

    users = response.json()

    assert isinstance(users, list)

    volunteer = next(user for user in users if user["id"] == str(volunteer_id))

    assert volunteer["username"] == "volunteer.maria"
    assert volunteer["role"] == "volunteer"
    assert volunteer["is_active"] is False

    assert any(user["role"] == "admin" for user in users)

    assert all("password_hash" not in user and "password" not in user for user in users)


def test_list_users_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _session = api_client

    response = client.get("/api/users")

    assert response.status_code == 401


def test_volunteer_cannot_list_users(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.get(
        "/api/users",
        headers=headers,
    )

    assert response.status_code == 403


def test_change_own_password_requires_authentication(api_client) -> None:
    client, _session = api_client

    response = client.patch(
        "/api/users/me/password",
        json={
            "current_password": "CurrentPassword123!",
            "new_password": "NewSecurePassword123!",
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["volunteer", "admin"])
def test_change_own_password_updates_password_hash(
    api_client,
    role: str,
) -> None:
    client, session = api_client

    current_password = "CurrentPassword123!"
    new_password = "NewSecurePassword123!"

    headers = create_authenticated_headers(session, role=role)

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    user_id = token_service.decode_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )

    user = session.get(UserModel, user_id)
    assert user is not None

    hasher = PasswordHasher()
    user.password_hash = hasher.hash(current_password)
    session.commit()

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": current_password,
            "new_password": new_password,
        },
    )

    assert response.status_code == 204

    session.refresh(user)

    assert hasher.verify(new_password, user.password_hash)
    assert not hasher.verify(current_password, user.password_hash)


def test_change_own_password_rejects_wrong_current_password(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="volunteer")

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    user_id = token_service.decode_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )

    user = session.get(UserModel, user_id)
    assert user is not None

    hasher = PasswordHasher()
    user.password_hash = hasher.hash("CorrectPassword123!")
    session.commit()

    original_hash = user.password_hash

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"

    session.refresh(user)

    assert user.password_hash == original_hash
    assert hasher.verify("CorrectPassword123!", user.password_hash)


def test_change_own_password_rejects_short_new_password(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="volunteer")

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    user_id = token_service.decode_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )

    user = session.get(UserModel, user_id)
    assert user is not None

    hasher = PasswordHasher()
    current_password = "CurrentPassword123!"
    user.password_hash = hasher.hash(current_password)
    session.commit()

    original_hash = user.password_hash

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": current_password,
            "new_password": "short",
        },
    )

    assert response.status_code == 422

    session.refresh(user)

    assert user.password_hash == original_hash
    assert hasher.verify(current_password, user.password_hash)


def test_change_own_password_requires_new_password(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": "CurrentPassword123!",
        },
    )

    assert response.status_code == 422


def test_change_own_password_rejects_whitespace_only_password(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="volunteer")

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    user_id = token_service.decode_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )

    user = session.get(UserModel, user_id)
    assert user is not None

    hasher = PasswordHasher()
    current_password = "CurrentPassword123!"
    user.password_hash = hasher.hash(current_password)
    session.commit()

    original_hash = user.password_hash

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": current_password,
            "new_password": "                ",
        },
    )

    assert response.status_code == 422

    session.refresh(user)

    assert user.password_hash == original_hash
    assert hasher.verify(current_password, user.password_hash)


def test_change_own_password_requires_current_password(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "new_password": "NewSecurePassword123!",
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]
    assert any(
        error["loc"] == ["body", "current_password"] and error["type"] == "missing"
        for error in errors
    )


def test_change_own_password_rejects_inactive_user(
    api_client,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    token_service = JwtTokenService(
        secret_key="test-secret-key-with-at-least-32-bytes",
        access_token_ttl=timedelta(minutes=30),
    )
    user_id = token_service.decode_access_token(
        headers["Authorization"].removeprefix("Bearer ")
    )

    user = session.get(UserModel, user_id)
    assert user is not None

    hasher = PasswordHasher()
    user.password_hash = hasher.hash("CurrentPassword123!")
    user.is_active = False
    session.commit()

    original_hash = user.password_hash

    response = client.patch(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": "CurrentPassword123!",
            "new_password": "NewSecurePassword123!",
        },
    )

    assert response.status_code == 401

    session.refresh(user)
    assert user.password_hash == original_hash


def test_list_services_filters_by_date_and_orders_by_start_time(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    morning_id = uuid4()
    evening_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=evening_id,
                name="Culto da Noite",
                starts_at=datetime(2026, 11, 22, 19, 0),
                ends_at=datetime(2026, 11, 22, 21, 0),
            ),
            ServiceModel(
                id=uuid4(),
                name="Culto de Outro Dia",
                starts_at=datetime(2026, 11, 29, 9, 0),
                ends_at=datetime(2026, 11, 29, 11, 0),
            ),
            ServiceModel(
                id=morning_id,
                name="Culto da Manhã",
                starts_at=datetime(2026, 11, 22, 9, 0),
                ends_at=datetime(2026, 11, 22, 11, 0),
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        "/api/services",
        params={"date": "2026-11-22"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "service_id": str(morning_id),
            "name": "Culto da Manhã",
            "starts_at": "2026-11-22T09:00:00",
            "ends_at": "2026-11-22T11:00:00",
        },
        {
            "service_id": str(evening_id),
            "name": "Culto da Noite",
            "starts_at": "2026-11-22T19:00:00",
            "ends_at": "2026-11-22T21:00:00",
        },
    ]


def test_list_services_returns_empty_list_for_date_without_services(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(verification_session)

    response = client.get(
        "/api/services",
        params={"date": "2026-11-22"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_services_without_date_returns_all_services(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(verification_session)

    service_id = uuid4()
    verification_session.add(
        ServiceModel(
            id=service_id,
            name="Culto Especial",
            starts_at=datetime(2026, 11, 22, 19, 0),
            ends_at=None,
        )
    )
    verification_session.commit()

    response = client.get("/api/services", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {
            "service_id": str(service_id),
            "name": "Culto Especial",
            "starts_at": "2026-11-22T19:00:00",
            "ends_at": None,
        }
    ]


def test_list_services_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get("/api/services")

    assert response.status_code == 401


def test_list_sessions_filters_by_service(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    service_id = uuid4()
    other_service_id = uuid4()
    nursery_room_id = uuid4()
    children_room_id = uuid4()
    nursery_session_id = uuid4()
    children_session_id = uuid4()

    verification_session.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Culto de Domingo",
                starts_at=datetime(2026, 11, 22, 9, 0),
                ends_at=None,
            ),
            ServiceModel(
                id=other_service_id,
                name="Outro Culto",
                starts_at=datetime(2026, 11, 29, 9, 0),
                ends_at=None,
            ),
            RoomModel(
                id=nursery_room_id,
                name="Berçário",
                normalized_name="bercario",
                is_active=True,
            ),
            RoomModel(
                id=children_room_id,
                name="Infantil",
                normalized_name="infantil",
                is_active=True,
            ),
        ]
    )
    verification_session.flush()

    verification_session.add_all(
        [
            SessionModel(
                id=children_session_id,
                service_id=service_id,
                room_id=children_room_id,
                name="Infantil",
                min_age_years=3,
                max_age_years=6,
                status="scheduled",
            ),
            SessionModel(
                id=nursery_session_id,
                service_id=service_id,
                room_id=nursery_room_id,
                name="Berçário",
                min_age_years=0,
                max_age_years=2,
                status="scheduled",
            ),
            SessionModel(
                id=uuid4(),
                service_id=other_service_id,
                room_id=nursery_room_id,
                name="Outro Berçário",
                min_age_years=0,
                max_age_years=2,
                status="scheduled",
            ),
        ]
    )
    verification_session.commit()

    response = client.get(
        "/api/sessions",
        params={"service_id": str(service_id)},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "session_id": str(nursery_session_id),
            "service_id": str(service_id),
            "room_id": str(nursery_room_id),
            "name": "Berçário",
            "min_age_years": 0,
            "max_age_years": 2,
            "status": "scheduled",
        },
        {
            "session_id": str(children_session_id),
            "service_id": str(service_id),
            "room_id": str(children_room_id),
            "name": "Infantil",
            "min_age_years": 3,
            "max_age_years": 6,
            "status": "scheduled",
        },
    ]


def test_list_sessions_returns_404_for_unknown_service(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(verification_session)

    response = client.get(
        "/api/sessions",
        params={"service_id": str(uuid4())},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Service not found"


def test_list_sessions_returns_empty_list_for_service_without_sessions(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(verification_session)
    service_id = uuid4()

    verification_session.add(
        ServiceModel(
            id=service_id,
            name="Culto Especial",
            starts_at=datetime(2026, 11, 22, 19, 0),
            ends_at=None,
        )
    )
    verification_session.commit()

    response = client.get(
        "/api/sessions",
        params={"service_id": str(service_id)},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_sessions_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get(
        "/api/sessions",
        params={"service_id": str(uuid4())},
    )

    assert response.status_code == 401


def test_get_admin_settings_returns_current_settings(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    verification_session.add(MinistrySettingsModel(pager_required=True))
    verification_session.commit()

    response = client.get(
        "/api/admin/settings",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "pager_required": True,
    }


def test_get_admin_settings_rejects_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.get(
        "/api/admin/settings",
        headers=headers,
    )

    assert response.status_code == 403


def test_create_service_rejects_room_without_age_range(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    verification_session.add(
        RoomModel(
            id=uuid4(),
            name="Sala sem configuração",
            normalized_name="sala sem configuracao",
            is_active=True,
            min_age_years=None,
            max_age_years=None,
        )
    )
    verification_session.commit()

    response = client.post(
        "/api/services",
        headers=headers,
        json={
            "name": "Culto 22/11/2026",
            "starts_at": "2026-11-22T09:00:00",
        },
    )

    assert response.status_code == 409
    assert "age range" in response.json()["detail"]

    services = verification_session.scalars(select(ServiceModel)).all()

    sessions = verification_session.scalars(select(SessionModel)).all()

    assert services == []
    assert sessions == []


def test_create_service_rolls_back_when_session_creation_fails(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client
    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    verification_session.add(
        RoomModel(
            id=uuid4(),
            name="Sala Infantil",
            normalized_name="sala infantil",
            is_active=True,
            min_age_years=3,
            max_age_years=5,
        )
    )
    verification_session.commit()

    with patch(
        "church_city_kids.api.main.SqlAlchemyCreateServiceRepository.add_session",
        side_effect=RuntimeError("Simulated session persistence failure"),
    ):
        response = client.post(
            "/api/services",
            headers=headers,
            json={
                "name": "Culto 22/11/2026",
                "starts_at": "2026-11-22T09:00:00",
            },
        )

    assert response.status_code == 500

    services = verification_session.scalars(select(ServiceModel)).all()

    sessions = verification_session.scalars(select(SessionModel)).all()

    assert services == []
    assert sessions == []


def test_update_room_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    room = RoomModel(
        id=uuid4(),
        name="Sala 1",
        normalized_name="sala 1",
        is_active=True,
        min_age_years=3,
        max_age_years=5,
    )
    verification_session.add(room)
    verification_session.commit()

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{room.id}",
        headers=headers,
        json={
            "name": "Berçário",
            "min_age_years": 2,
            "max_age_years": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    verification_session.refresh(room)

    assert room.name == "Berçário"
    assert room.normalized_name == "berçário"
    assert room.min_age_years == 2
    assert room.max_age_years == 3
    assert room.is_active is True


def test_update_room_preserves_fields_not_provided(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    room = RoomModel(
        id=uuid4(),
        name="Sala 1",
        normalized_name="sala 1",
        is_active=True,
        min_age_years=3,
        max_age_years=5,
    )
    verification_session.add(room)
    verification_session.commit()

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{room.id}",
        headers=headers,
        json={"name": "Sala Infantil"},
    )

    assert response.status_code == 200

    verification_session.refresh(room)

    assert room.name == "Sala Infantil"
    assert room.min_age_years == 3
    assert room.max_age_years == 5


def test_update_room_returns_404_when_room_does_not_exist(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{uuid4()}",
        headers=headers,
        json={"name": "Berçário"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Room not found"}


def test_update_room_rejects_duplicate_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    first_room = RoomModel(
        id=uuid4(),
        name="Sala 1",
        normalized_name="sala 1",
        is_active=True,
    )
    second_room = RoomModel(
        id=uuid4(),
        name="Sala 2",
        normalized_name="sala 2",
        is_active=True,
    )

    verification_session.add_all([first_room, second_room])
    verification_session.commit()

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{second_room.id}",
        headers=headers,
        json={"name": "Sala 1"},
    )

    assert response.status_code == 409

    verification_session.refresh(second_room)
    assert second_room.name == "Sala 2"


def test_update_room_rejects_invalid_age_range(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    room = RoomModel(
        id=uuid4(),
        name="Sala 1",
        normalized_name="sala 1",
        is_active=True,
        min_age_years=3,
        max_age_years=5,
    )
    verification_session.add(room)
    verification_session.commit()

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{room.id}",
        headers=headers,
        json={
            "min_age_years": 7,
            "max_age_years": 5,
        },
    )

    assert response.status_code == 422

    verification_session.refresh(room)
    assert room.min_age_years == 3
    assert room.max_age_years == 5


def test_update_room_rejects_empty_patch(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{uuid4()}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_update_room_rejects_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    headers = create_authenticated_headers(
        verification_session,
        role="volunteer",
    )

    response = client.patch(
        f"/api/rooms/{uuid4()}",
        headers=headers,
        json={"name": "Berçário"},
    )

    assert response.status_code == 403


def test_update_room_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.patch(
        f"/api/rooms/{uuid4()}",
        json={"name": "Berçário"},
    )

    assert response.status_code == 401


def test_update_room_does_not_modify_existing_sessions(
    api_client: tuple[TestClient, Session],
) -> None:
    client, verification_session = api_client

    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()

    verification_session.add(
        ServiceModel(
            id=service_id,
            name="Culto de Domingo",
            starts_at=datetime(2026, 11, 22, 9, 0),
        )
    )
    verification_session.flush()

    room = RoomModel(
        id=room_id,
        name="Sala 1",
        normalized_name="sala 1",
        is_active=True,
        min_age_years=3,
        max_age_years=5,
    )

    verification_session.add(room)
    verification_session.flush()

    existing_session = SessionModel(
        id=session_id,
        service_id=service_id,
        room_id=room_id,
        name="Sala 1",
        min_age_years=3,
        max_age_years=5,
        status="scheduled",
    )

    verification_session.add(existing_session)
    verification_session.commit()

    headers = create_authenticated_headers(
        verification_session,
        role="admin",
    )

    response = client.patch(
        f"/api/rooms/{room_id}",
        headers=headers,
        json={
            "name": "Sala Infantil",
            "min_age_years": 2,
            "max_age_years": 6,
        },
    )

    assert response.status_code == 200

    verification_session.refresh(existing_session)

    assert existing_session.name == "Sala 1"
    assert existing_session.min_age_years == 3
    assert existing_session.max_age_years == 5


def test_admin_can_create_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    initial_user_count = session.query(UserModel).count()

    response = client.post(
        "/api/volunteers",
        json={"full_name": "  Maria Oliveira  "},
        headers=headers,
    )

    assert response.status_code == 201

    response_data = response.json()

    volunteer_id = UUID(response_data["id"])

    assert response_data == {
        "id": str(volunteer_id),
        "full_name": "Maria Oliveira",
        "is_active": True,
    }

    session.expire_all()

    saved_volunteer = session.get(VolunteerModel, volunteer_id)

    assert saved_volunteer is not None
    assert saved_volunteer.full_name == "Maria Oliveira"
    assert saved_volunteer.is_active is True

    # Creating a volunteer must not create a user account.
    assert session.query(UserModel).count() == initial_user_count


def test_create_volunteer_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    response = client.post(
        "/api/volunteers",
        json={"full_name": "Maria Oliveira"},
    )

    assert response.status_code == 401
    assert session.query(VolunteerModel).count() == 0


def test_volunteer_cannot_create_another_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    response = client.post(
        "/api/volunteers",
        json={"full_name": "Maria Oliveira"},
        headers=headers,
    )

    assert response.status_code == 403
    assert session.query(VolunteerModel).count() == 0


@pytest.mark.parametrize(
    "full_name",
    ["", "   ", "\t", "\n"],
)
def test_create_volunteer_rejects_blank_name(
    api_client: tuple[TestClient, Session],
    full_name: str,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    response = client.post(
        "/api/volunteers",
        json={"full_name": full_name},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ("Volunteer name cannot be blank")

    assert session.query(VolunteerModel).count() == 0


def test_list_volunteers_returns_empty_list(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    response = client.get(
        "/api/volunteers",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_list_volunteers(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="admin",
    )

    volunteer_a = VolunteerModel(
        id=uuid4(),
        full_name="Carlos Santos",
        is_active=True,
    )
    volunteer_b = VolunteerModel(
        id=uuid4(),
        full_name="Ana Oliveira",
        is_active=True,
    )
    volunteer_c = VolunteerModel(
        id=uuid4(),
        full_name="Bruno Silva",
        is_active=False,
    )

    session.add_all([volunteer_a, volunteer_b, volunteer_c])
    session.commit()

    response = client.get(
        "/api/volunteers",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert [item["full_name"] for item in data] == [
        "Ana Oliveira",
        "Bruno Silva",
        "Carlos Santos",
    ]

    assert [item["is_active"] for item in data] == [
        True,
        False,
        True,
    ]

    assert all(set(item.keys()) == {"id", "full_name", "is_active"} for item in data)


def test_volunteer_can_list_volunteers(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )

    session.add(volunteer)
    session.commit()

    response = client.get(
        "/api/volunteers",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["full_name"] == "Maria Oliveira"


def test_list_volunteers_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    response = client.get("/api/volunteers")

    assert response.status_code == 401
    assert session.query(VolunteerModel).count() == 0


def test_admin_can_update_volunteer_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": "Maria Santos"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

    session.expire_all()
    updated = session.get(VolunteerModel, volunteer.id)

    assert updated is not None
    assert updated.full_name == "Maria Santos"
    assert updated.is_active is True


def test_update_volunteer_strips_name_whitespace(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": "  Maria Santos  "},
        headers=headers,
    )

    assert response.status_code == 200

    session.expire_all()
    updated = session.get(VolunteerModel, volunteer.id)

    assert updated is not None
    assert updated.full_name == "Maria Santos"


@pytest.mark.parametrize(
    "full_name",
    ["", "   ", "\t", "\n", None],
)
def test_update_volunteer_rejects_blank_name(
    api_client: tuple[TestClient, Session],
    full_name: str | None,
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": full_name},
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()
    unchanged = session.get(VolunteerModel, volunteer.id)

    assert unchanged is not None
    assert unchanged.full_name == "Maria Oliveira"


def test_update_volunteer_rejects_empty_request(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={},
        headers=headers,
    )

    assert response.status_code == 422

    session.expire_all()
    unchanged = session.get(VolunteerModel, volunteer.id)

    assert unchanged is not None
    assert unchanged.full_name == "Maria Oliveira"


def test_update_volunteer_returns_404_for_unknown_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    response = client.patch(
        f"/api/volunteers/{uuid4()}",
        json={"full_name": "Maria Santos"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Volunteer not found"


def test_update_volunteer_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": "Maria Santos"},
    )

    assert response.status_code == 401

    session.expire_all()
    unchanged = session.get(VolunteerModel, volunteer.id)

    assert unchanged is not None
    assert unchanged.full_name == "Maria Oliveira"


def test_volunteer_cannot_update_another_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(
        session,
        role="volunteer",
    )

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=True,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": "Maria Santos"},
        headers=headers,
    )

    assert response.status_code == 403

    session.expire_all()
    unchanged = session.get(VolunteerModel, volunteer.id)

    assert unchanged is not None
    assert unchanged.full_name == "Maria Oliveira"


def test_update_inactive_volunteer_preserves_inactive_status(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    headers = create_authenticated_headers(session, role="admin")

    volunteer = VolunteerModel(
        id=uuid4(),
        full_name="Maria Oliveira",
        is_active=False,
    )
    session.add(volunteer)
    session.commit()

    response = client.patch(
        f"/api/volunteers/{volunteer.id}",
        json={"full_name": "Maria Santos"},
        headers=headers,
    )

    assert response.status_code == 200

    session.expire_all()
    updated = session.get(VolunteerModel, volunteer.id)

    assert updated is not None
    assert updated.full_name == "Maria Santos"
    assert updated.is_active is False


def create_volunteer_assignment_scenario(
    db: Session,
    *,
    volunteer_active: bool = True,
) -> tuple[UUID, UUID, UUID]:
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    volunteer_id = uuid4()

    db.add_all(
        [
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 11, 8, 10, 0),
                ends_at=None,
            ),
            RoomModel(
                id=room_id,
                name="Sala Infantil",
                is_active=True,
            ),
            VolunteerModel(
                id=volunteer_id,
                full_name="Maria Oliveira",
                is_active=volunteer_active,
            ),
        ]
    )
    db.flush()

    db.add(
        SessionModel(
            id=session_id,
            service_id=service_id,
            room_id=room_id,
            name="Infantil 3-5",
            min_age_years=3,
            max_age_years=5,
            status="scheduled",
        )
    )
    db.commit()

    return service_id, session_id, volunteer_id


def test_assign_volunteer_creates_assignment_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    service_id, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={
            "volunteer_id": str(volunteer_id),
            "role": "Teacher",
        },
    )

    assert response.status_code == 201

    assignment_id = UUID(response.json()["assignment_id"])
    assignment = db.get(VolunteerAssignmentModel, assignment_id)

    assert assignment is not None
    assert assignment.service_id == service_id
    assert assignment.session_id == session_id
    assert assignment.volunteer_id == volunteer_id
    assert assignment.role == "Teacher"


def test_assign_volunteer_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    _, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        json={"volunteer_id": str(volunteer_id)},
    )

    assert response.status_code == 401
    assert db.query(VolunteerAssignmentModel).count() == 0


def test_assign_volunteer_returns_404_for_unknown_session(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")

    response = client.post(
        f"/api/sessions/{uuid4()}/volunteers",
        headers=headers,
        json={"volunteer_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}
    assert db.query(VolunteerAssignmentModel).count() == 0


def test_assign_volunteer_returns_404_for_unknown_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    _, session_id, _ = create_volunteer_assignment_scenario(db)

    response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={"volunteer_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Volunteer not found"}
    assert db.query(VolunteerAssignmentModel).count() == 0


def test_assign_volunteer_returns_409_for_inactive_volunteer(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    _, session_id, volunteer_id = create_volunteer_assignment_scenario(
        db,
        volunteer_active=False,
    )

    response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={"volunteer_id": str(volunteer_id)},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Volunteer is inactive"}
    assert db.query(VolunteerAssignmentModel).count() == 0


def test_assign_volunteer_returns_409_for_duplicate(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    _, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    url = f"/api/sessions/{session_id}/volunteers"
    payload = {"volunteer_id": str(volunteer_id)}

    first_response = client.post(
        url,
        headers=headers,
        json=payload,
    )
    second_response = client.post(
        url,
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "Volunteer already assigned to this service"
    }
    assert db.query(VolunteerAssignmentModel).count() == 1


def test_list_service_volunteers_returns_assignments(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    service_id, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    create_response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={
            "volunteer_id": str(volunteer_id),
            "role": "Teacher",
        },
    )
    assert create_response.status_code == 201

    response = client.get(
        f"/api/services/{service_id}/volunteers",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "assignment_id": create_response.json()["assignment_id"],
            "service_id": str(service_id),
            "session_id": str(session_id),
            "volunteer_id": str(volunteer_id),
            "volunteer_name": "Maria Oliveira",
            "role": "Teacher",
        }
    ]


def test_list_service_volunteers_returns_empty_list(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    service_id, _, _ = create_volunteer_assignment_scenario(db)

    response = client.get(
        f"/api/services/{service_id}/volunteers",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_service_volunteers_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    service_id, _, _ = create_volunteer_assignment_scenario(db)

    response = client.get(
        f"/api/services/{service_id}/volunteers",
    )

    assert response.status_code == 401


def test_list_service_volunteers_returns_404_for_unknown_service(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")

    response = client.get(
        f"/api/services/{uuid4()}/volunteers",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Service not found"}


def test_remove_volunteer_assignment_via_api(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    _, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    create_response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={"volunteer_id": str(volunteer_id)},
    )
    assert create_response.status_code == 201

    assignment_id = UUID(create_response.json()["assignment_id"])

    response = client.delete(
        f"/api/volunteer-assignments/{assignment_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert db.get(VolunteerAssignmentModel, assignment_id) is None
    assert db.get(VolunteerModel, volunteer_id) is not None


def test_remove_volunteer_assignment_returns_404_for_unknown_assignment(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")

    response = client.delete(
        f"/api/volunteer-assignments/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Volunteer assignment not found",
    }


def test_remove_volunteer_assignment_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, db = api_client
    headers = create_authenticated_headers(db, role="volunteer")
    _, session_id, volunteer_id = create_volunteer_assignment_scenario(db)

    create_response = client.post(
        f"/api/sessions/{session_id}/volunteers",
        headers=headers,
        json={"volunteer_id": str(volunteer_id)},
    )
    assert create_response.status_code == 201

    assignment_id = UUID(create_response.json()["assignment_id"])

    response = client.delete(
        f"/api/volunteer-assignments/{assignment_id}",
    )

    assert response.status_code == 401
    assert db.get(VolunteerAssignmentModel, assignment_id) is not None
