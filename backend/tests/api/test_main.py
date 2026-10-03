from collections.abc import Generator
from datetime import date, datetime
from uuid import UUID

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
    ServiceModel,
)


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_child(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    def override_get_db_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as client:
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
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201

    body = response.json()

    assert "family_id" in body
    assert "child_id" in body
    assert "guardian_id" in body

    child_id = UUID(body["child_id"])
    family_id = UUID(body["family_id"])
    guardian_id = UUID(body["guardian_id"])

    with Session(engine) as session:
        child = session.get(ChildModel, child_id)
        family = session.get(FamilyModel, family_id)
        guardian = session.get(GuardianModel, guardian_id)

        assert child is not None
        assert child.full_name == "Maria Silva"
        assert child.birth_date == date(2021, 5, 10)

        assert family is not None

        assert guardian is not None
        assert guardian.full_name == "Ana Silva"
        assert guardian.phone == "82999999999"


def test_create_service(tmp_path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    def override_get_db_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/services",
                json={
                    "name": "Sunday Service",
                    "starts_at": "2026-10-04T19:00:00",
                    "ends_at": "2026-10-04T21:00:00",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201

    body = response.json()
    service_id = UUID(body["service_id"])

    with Session(engine) as session:
        service = session.get(ServiceModel, service_id)

        assert service is not None
        assert service.name == "Sunday Service"
        assert service.starts_at == datetime(2026, 10, 4, 19, 0)
        assert service.ends_at == datetime(2026, 10, 4, 21, 0)
