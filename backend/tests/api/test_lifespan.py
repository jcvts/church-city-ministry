import sqlite3
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from church_city_kids.api.main import app


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

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

    backup_directory = tmp_path / "backups"
    backups = list(backup_directory.glob("*.db"))

    assert backups

    with sqlite3.connect(backups[0]) as connection:
        children = connection.execute("SELECT id FROM children").fetchall()

    assert children == [(1,)]
