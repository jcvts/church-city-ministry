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
    Base,
    ChildModel,
    FamilyModel,
    GuardianModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)


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
                id=active_room_id,  # Correção aqui
                name="Sala Infantil",
                is_active=True,
            ),
            RoomModel(
                id=uuid4(),
                name="Sala Desativada",
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
