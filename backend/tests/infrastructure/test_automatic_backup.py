import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from unittest.mock import Mock, patch

from church_city_kids.infrastructure.persistence.automatic_backup import (
    AutomaticBackupManager,
)


def test_start_creates_backup_when_none_exists(tmp_path: Path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
    )

    manager.start()

    create_backup.assert_called_once()

    assert create_backup.call_args.kwargs["source_path"] == database_path
    assert (
        create_backup.call_args.kwargs["backup_directory"]
        == backup_directory
    )
    assert isinstance(
        create_backup.call_args.kwargs["timestamp"],
        datetime,
    )


def test_start_skips_backup_when_one_already_exists(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    existing_backup = (
        backup_directory / "church_city_kids_20261101_115800.db"
    )
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(existing_backup) as destination:
            source.backup(destination)

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 1, 12, 0, 0),
    )

    manager.start()

    create_backup.assert_not_called()


def test_start_creates_backup_when_existing_backup_is_invalid(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    invalid_backup = (
        backup_directory / "church_city_kids_20261101_100000.db"
    )
    invalid_backup.write_bytes(b"Not a valid SQLite database")

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
    )

    manager.start()

    create_backup.assert_called_once()


def test_start_creates_backup_when_existing_backup_is_old(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    old_backup = (
        backup_directory / "church_city_kids_20261029_100000.db"
    )

    with sqlite3.connect(old_backup) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 1, 12, 0, 0),
    )

    manager.start()

    create_backup.assert_called_once()


def test_start_skips_backup_at_exact_age_limit(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    existing_backup = (
        backup_directory / "church_city_kids_20261101_115500.db"
    )

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(existing_backup) as destination:
            source.backup(destination)

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 1, 12, 0, 0),
    )

    manager.start()

    create_backup.assert_not_called()


def test_start_creates_backup_just_after_age_limit(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    existing_backup = (
        backup_directory / "church_city_kids_20261031_115959.db"
    )

    with sqlite3.connect(existing_backup) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 1, 12, 0, 0),
    )

    manager.start()

    create_backup.assert_called_once()


def test_run_backup_if_needed_creates_backup_when_none_exists(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    create_backup = Mock()

    current_time = datetime(2026, 11, 1, 12, 0, 0)

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: current_time,
    )

    manager.run_backup_if_needed()

    create_backup.assert_called_once_with(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=current_time,
    )


def test_backup_worker_runs_periodically_until_stopped() -> None:
    manager = AutomaticBackupManager(
        database_path=Path("/tmp/church_city_kids.db"),
        backup_directory=Path("/tmp/backups"),
    )

    manager.run_backup_if_needed = Mock()

    stop_event = Mock(spec=Event)
    stop_event.wait.side_effect = [False, False, True]

    manager._run_worker(
        stop_event=stop_event,
        interval_seconds=60,
    )

    assert manager.run_backup_if_needed.call_count == 2

    assert stop_event.wait.call_count == 3
    stop_event.wait.assert_called_with(60)


def test_start_creates_background_backup_thread(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=Mock(),
    )

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
    ) as thread_class:
        manager.start()

    thread_class.assert_called_once()

    thread = thread_class.return_value
    thread.start.assert_called_once()

    assert thread_class.call_args.kwargs["daemon"] is True
    assert thread_class.call_args.kwargs["target"] == manager._run_worker


def test_stop_signals_worker_and_waits_for_thread(
    tmp_path: Path,
) -> None:
    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=Mock(),
    )

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
    ) as thread_class:
        manager.start()

        thread = thread_class.return_value

        with patch.object(
            manager._stop_event,
            "set",
            wraps=manager._stop_event.set,
        ) as signal_stop:
            manager.stop()

    signal_stop.assert_called_once()
    thread.join.assert_called_once_with()


def test_start_does_not_create_multiple_threads(
    tmp_path: Path,
) -> None:
    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=create_backup,
    )

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
    ) as thread_class:
        manager.start()
        manager.start()

        thread_class.assert_called_once()
        thread_class.return_value.start.assert_called_once()

    create_backup.assert_called_once()


def test_backup_worker_continues_after_backup_failure() -> None:
    manager = AutomaticBackupManager(
        database_path=Path("/tmp/church_city_kids.db"),
        backup_directory=Path("/tmp/backups"),
    )

    manager.run_backup_if_needed = Mock(
        side_effect=[
            OSError("Disk temporarily unavailable"),
            None,
        ]
    )

    stop_event = Mock(spec=Event)
    stop_event.wait.side_effect = [False, False, True]

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.logger"
    ) as logger:
        manager._run_worker(
            stop_event=stop_event,
            interval_seconds=60,
        )

    assert manager.run_backup_if_needed.call_count == 2

    logger.exception.assert_called_once_with(
        "Automatic database backup failed"
    )


def test_start_continues_when_initial_backup_fails(
    tmp_path: Path,
) -> None:
    create_backup = Mock(
        side_effect=OSError("Backup disk unavailable")
    )

    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=create_backup,
    )

    with (
        patch(
            "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
        ) as thread_class,
        patch(
            "church_city_kids.infrastructure.persistence.automatic_backup.logger"
        ) as logger,
    ):
        manager.start()

    create_backup.assert_called_once()
    logger.exception.assert_called_once_with(
        "Initial automatic database backup failed"
    )

    thread_class.assert_called_once()
    thread_class.return_value.start.assert_called_once()


def test_initial_backup_failure_updates_error_status(
    tmp_path: Path,
) -> None:
    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=Mock(
            side_effect=OSError("Backup disk unavailable")
        ),
    )

    with (
        patch(
            "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
        ),
        patch(
            "church_city_kids.infrastructure.persistence.automatic_backup.logger"
        ),
    ):
        manager.start()

    assert manager.last_error == "Backup disk unavailable"


def test_periodic_backup_failure_updates_error_status() -> None:
    manager = AutomaticBackupManager(
        database_path=Path("/tmp/church_city_kids.db"),
        backup_directory=Path("/tmp/backups"),
    )

    manager.run_backup_if_needed = Mock(
        side_effect=OSError("Periodic backup failed")
    )

    stop_event = Mock(spec=Event)
    stop_event.wait.side_effect = [False, True]

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.logger"
    ):
        manager._run_worker(
            stop_event=stop_event,
            interval_seconds=60,
        )

    assert manager.last_error == "Periodic backup failed"


def test_periodic_backup_success_clears_previous_error() -> None:
    manager = AutomaticBackupManager(
        database_path=Path("/tmp/church_city_kids.db"),
        backup_directory=Path("/tmp/backups"),
    )

    manager.last_error = "Previous backup failed"

    manager.run_backup_if_needed = Mock(return_value=None)

    stop_event = Mock(spec=Event)
    stop_event.wait.side_effect = [False, True]

    manager._run_worker(
        stop_event=stop_event,
        interval_seconds=60,
    )

    assert manager.run_backup_if_needed.call_count == 1
    assert manager.last_error is None


def test_successful_initial_backup_clears_previous_error(
    tmp_path: Path,
) -> None:
    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=Mock(),
    )

    manager.last_error = "Previous backup failed"

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.Thread"
    ):
        manager.start()

    assert manager.last_error is None


def test_backup_is_created_when_interval_has_elapsed(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    existing_backup = (
        backup_directory / "church_city_kids_20261102_100000.db"
    )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(existing_backup) as destination:
            source.backup(destination)

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 2, 10, 16, 0),
        max_backup_age=timedelta(minutes=15),
    )

    manager.run_backup_if_needed()

    create_backup.assert_called_once()


def test_recent_backup_is_reused_even_when_database_changes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE backup_test (id INTEGER PRIMARY KEY)"
        )

    existing_backup = (
        backup_directory / "church_city_kids_20261102_100000.db"
    )

    with sqlite3.connect(database_path) as source:
        with sqlite3.connect(existing_backup) as destination:
            source.backup(destination)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO backup_test (id) VALUES (1)"
        )

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: datetime(2026, 11, 2, 10, 5, 0),
        max_backup_age=timedelta(minutes=15),
    )

    manager.run_backup_if_needed()

    create_backup.assert_not_called()


def test_stop_creates_final_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    current_time = datetime(2026, 11, 2, 12, 0, 0)

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: current_time,
    )

    manager._thread = Mock(spec=Thread)

    manager.stop()

    create_backup.assert_called_once_with(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=current_time,
    )

    assert manager._thread is None


def test_stop_continues_when_final_backup_fails(
    tmp_path: Path,
) -> None:
    create_backup = Mock(
        side_effect=OSError("Backup destination unavailable")
    )

    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=create_backup,
    )

    thread = Mock(spec=Thread)
    manager._thread = thread

    with patch(
        "church_city_kids.infrastructure.persistence.automatic_backup.logger"
    ) as logger:
        manager.stop()

    thread.join.assert_called_once()
    create_backup.assert_called_once()
    logger.exception.assert_called_once_with(
        "Final automatic database backup failed"
    )

    assert manager._thread is None
    assert manager.last_error == "Backup destination unavailable"


def test_stop_waits_for_worker_before_final_backup(
    tmp_path: Path,
) -> None:
    operations = []

    thread = Mock(spec=Thread)
    thread.join.side_effect = lambda: operations.append("worker_joined")

    create_backup = Mock(
        side_effect=lambda **kwargs: operations.append("final_backup")
    )

    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
        create_backup=create_backup,
    )

    manager._thread = thread

    manager.stop()

    assert operations == ["worker_joined", "final_backup"]
    thread.join.assert_called_once()
    create_backup.assert_called_once()


def test_recent_backup_with_collision_suffix_is_reused(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    current_time = datetime(2026, 11, 2, 12, 0, 0)

    backup_path = (
        backup_directory
        / "church_city_kids_20261102_115500_1.db"
    )

    with sqlite3.connect(backup_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY)"
        )

    create_backup = Mock()

    manager = AutomaticBackupManager(
        database_path=database_path,
        backup_directory=backup_directory,
        create_backup=create_backup,
        now=lambda: current_time,
        max_backup_age=timedelta(minutes=15),
    )

    manager.run_backup_if_needed()

    create_backup.assert_not_called()


def test_default_backup_max_age_is_five_minutes(
    tmp_path: Path,
) -> None:
    manager = AutomaticBackupManager(
        database_path=tmp_path / "church_city_kids.db",
        backup_directory=tmp_path / "backups",
    )

    assert manager.max_backup_age == timedelta(minutes=5)
