import sqlite3
from datetime import date, time
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from church_city_kids.api.main import app
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    Base,
    RecurringServiceScheduleModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)


def test_lifespan_starts_and_stops_backup_manager() -> None:
    backup_manager = Mock()

    app.state.backup_manager = backup_manager

    try:
        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            backup_manager.start.assert_called_once()
            backup_manager.stop.assert_not_called()

        backup_manager.stop.assert_called_once()
    finally:
        del app.state.backup_manager


def test_lifespan_stops_backup_manager_on_error() -> None:
    backup_manager = Mock()
    app.state.backup_manager = backup_manager

    try:
        with pytest.raises(RuntimeError, match="Simulated failure"):
            with TestClient(app):
                backup_manager.start.assert_called_once()
                raise RuntimeError("Simulated failure")

        backup_manager.stop.assert_called_once()
    finally:
        del app.state.backup_manager


def test_lifespan_creates_real_database_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "church_city_kids.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO children (id) VALUES (1)")

    monkeypatch.setenv(
        "CHURCH_CITY_KIDS_DB_PATH",
        str(database_path),
    )

    monkeypatch.setenv(
        "CHURCH_CITY_JWT_SECRET_KEY",
        "test-only-jwt-secret-key-at-least-32-bytes",
    )

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

    backup_directory = tmp_path / "backups"
    backups = list(backup_directory.glob("*.db"))

    assert backups

    with sqlite3.connect(backups[0]) as connection:
        children = connection.execute("SELECT id FROM children").fetchall()

    assert children == [(1,)]


def test_generate_todays_services_creates_service_and_room_sessions(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "recurring.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            RecurringServiceScheduleModel(
                name="Culto da Manhã",
                weekday=6,
                starts_at=time(9, 0),
                ends_at=time(11, 0),
                is_active=True,
            )
        )
        session.add(
            RoomModel(
                id=uuid4(),
                name="Sala 1",
                normalized_name="sala 1",
                min_age_years=3,
                max_age_years=5,
                is_active=True,
            )
        )
        session.commit()

    from church_city_kids.api.main import generate_todays_services

    generate_todays_services(engine, date(2026, 11, 8))

    with Session(engine) as session:
        services = session.scalars(select(ServiceModel)).all()
        sessions = session.scalars(select(SessionModel)).all()

        assert len(services) == 1
        assert services[0].name == "Culto da Manhã"
        assert len(sessions) == 1
        assert sessions[0].service_id == services[0].id

    engine.dispose()


def test_generate_todays_services_does_not_duplicate_on_restart(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "recurring_restart.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            RecurringServiceScheduleModel(
                name="Culto da Manhã",
                weekday=6,
                starts_at=time(9, 0),
                ends_at=time(11, 0),
                is_active=True,
            )
        )
        session.add(
            RoomModel(
                id=uuid4(),
                name="Sala 1",
                normalized_name="sala 1",
                min_age_years=3,
                max_age_years=5,
                is_active=True,
            )
        )
        session.commit()

    from church_city_kids.api.main import generate_todays_services

    target_date = date(2026, 11, 8)

    # Simula duas inicializações no mesmo dia.
    generate_todays_services(engine, target_date)
    generate_todays_services(engine, target_date)

    with Session(engine) as session:
        services = session.scalars(select(ServiceModel)).all()
        sessions = session.scalars(select(SessionModel)).all()

        assert len(services) == 1
        assert len(sessions) == 1
        assert sessions[0].service_id == services[0].id

    engine.dispose()


def test_lifespan_generates_recurring_services_on_startup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_sqlite_engine(tmp_path / "startup.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            RecurringServiceScheduleModel(
                name="Culto da Manhã",
                weekday=date.today().weekday(),
                starts_at=time(9, 0),
                ends_at=time(11, 0),
                is_active=True,
            )
        )
        session.add(
            RoomModel(
                id=uuid4(),
                name="Sala 1",
                normalized_name="sala 1",
                min_age_years=3,
                max_age_years=5,
                is_active=True,
            )
        )
        session.commit()

    monkeypatch.setattr(
        "church_city_kids.api.main.engine",
        engine,
    )

    backup_manager = Mock()
    app.state.backup_manager = backup_manager

    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200

        with Session(engine) as session:
            services = session.scalars(select(ServiceModel)).all()
            sessions = session.scalars(select(SessionModel)).all()

            assert len(services) == 1
            assert services[0].name == "Culto da Manhã"
            assert len(sessions) == 1

        backup_manager.start.assert_called_once()
        backup_manager.stop.assert_called_once()
    finally:
        del app.state.backup_manager
        engine.dispose()
