import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from church_city_kids.infrastructure.persistence.database_backup import (
    backup_sqlite_database,
    create_timestamped_backup,
    prune_old_backups,
)


def test_backup_preserves_database_records(tmp_path) -> None:
    source_path = tmp_path / "church_city_kids.db"
    backup_path = tmp_path / "backups" / "church_city_kids_backup.db"

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    backup_sqlite_database(source_path, backup_path)

    assert backup_path.is_file()

    with sqlite3.connect(backup_path) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

    assert records == [("Maria",)]


def test_backup_rejects_missing_source_database(tmp_path) -> None:
    source_path = tmp_path / "missing.db"
    backup_path = tmp_path / "backups" / "backup.db"

    with pytest.raises(FileNotFoundError):
        backup_sqlite_database(source_path, backup_path)

    assert not source_path.exists()
    assert not backup_path.exists()


def test_backup_preserves_committed_wal_records(tmp_path) -> None:
    source_path = tmp_path / "church_city_kids.db"
    backup_path = tmp_path / "backups" / "backup.db"

    with sqlite3.connect(source_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Pedro",),
        )
        connection.commit()

        backup_sqlite_database(source_path, backup_path)

    with sqlite3.connect(backup_path) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

    assert records == [("Pedro",)]
    assert integrity == ("ok",)


def test_restore_database_preserves_records(tmp_path) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        restore_sqlite_database,
    )

    source_path = tmp_path / "original.db"
    backup_path = tmp_path / "backups" / "backup.db"
    restored_path = tmp_path / "restored" / "church_city_kids.db"

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    backup_sqlite_database(source_path, backup_path)

    restore_sqlite_database(backup_path, restored_path)

    assert restored_path.is_file()

    with sqlite3.connect(restored_path) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

    assert records == [("Maria",)]
    assert integrity == ("ok",)


def test_restore_rejects_existing_database_without_modifying_it(
    tmp_path,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        restore_sqlite_database,
    )

    backup_path = tmp_path / "backup.db"
    restore_path = tmp_path / "church_city_kids.db"

    with sqlite3.connect(backup_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    with sqlite3.connect(restore_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Pedro",),
        )
        connection.commit()

    with pytest.raises(FileExistsError):
        restore_sqlite_database(backup_path, restore_path)

    with sqlite3.connect(restore_path) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

    assert records == [("Pedro",)]


def test_restore_rejects_missing_backup_without_creating_database(
    tmp_path,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        restore_sqlite_database,
    )

    backup_path = tmp_path / "backups" / "missing.db"
    restore_path = tmp_path / "restored" / "church_city_kids.db"

    with pytest.raises(FileNotFoundError):
        restore_sqlite_database(backup_path, restore_path)

    assert not backup_path.exists()
    assert not restore_path.exists()


def test_restore_rejects_invalid_backup_without_leaving_database(
    tmp_path,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        restore_sqlite_database,
    )

    backup_path = tmp_path / "backups" / "corrupted.db"
    restore_path = tmp_path / "restored" / "church_city_kids.db"

    backup_path.parent.mkdir(parents=True)
    backup_path.write_bytes(b"This is not a valid SQLite database")

    with pytest.raises(sqlite3.DatabaseError):
        restore_sqlite_database(backup_path, restore_path)

    assert not restore_path.exists()
    assert list(restore_path.parent.glob(".restore_*.db")) == []


def test_backup_rejects_existing_destination_without_modifying_it(
    tmp_path,
) -> None:
    source_path = tmp_path / "church_city_kids.db"
    backup_path = tmp_path / "backups" / "backup.db"

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    backup_sqlite_database(source_path, backup_path)

    original_backup = backup_path.read_bytes()

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Pedro",),
        )
        connection.commit()

    with pytest.raises(FileExistsError):
        backup_sqlite_database(source_path, backup_path)

    assert backup_path.read_bytes() == original_backup

    with sqlite3.connect(backup_path) as connection:
        records = connection.execute(
            "SELECT name FROM children ORDER BY id"
        ).fetchall()

    assert records == [("Maria",)]
    assert list(backup_path.parent.glob(".backup_*.db")) == []


def test_create_timestamped_backup_uses_datetime_in_filename(
    tmp_path,
) -> None:
    from datetime import datetime

    from church_city_kids.infrastructure.persistence.database_backup import (
        create_timestamped_backup,
    )

    source_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    backup_path = create_timestamped_backup(
        source_path,
        backup_directory,
        datetime(2026, 11, 1, 9, 30, 45),
    )

    assert backup_path == (
        backup_directory / "church_city_kids_20261101_093045.db"
    )
    assert backup_path.is_file()

    with sqlite3.connect(backup_path) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

    assert records == [("Maria",)]


def test_timestamped_backup_preserves_existing_file_on_collision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    timestamp = datetime(2026, 11, 2, 12, 0, 0)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY)"
        )

    first_backup = create_timestamped_backup(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=timestamp,
    )

    original_contents = first_backup.read_bytes()

    second_backup = create_timestamped_backup(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=timestamp,
    )

    assert first_backup != second_backup
    assert first_backup.read_bytes() == original_contents
    assert second_backup.exists()


def test_prune_old_backups_keeps_most_recent_files(tmp_path) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        prune_old_backups,
    )

    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    filenames = [
        "church_city_kids_20261028_090000.db",
        "church_city_kids_20261029_090000.db",
        "church_city_kids_20261030_090000.db",
        "church_city_kids_20261031_090000.db",
        "church_city_kids_20261101_090000.db",
    ]

    for filename in filenames:
        with sqlite3.connect(backup_directory / filename) as connection:
            connection.execute(
                "CREATE TABLE children (id INTEGER PRIMARY KEY)"
            )
            connection.commit()

    prune_old_backups(
        backup_directory,
        keep_count=3,
    )

    remaining = sorted(
        path.name for path in backup_directory.glob("*.db")
    )

    assert remaining == filenames[-3:]


def test_prune_old_backups_ignores_unrelated_and_invalid_files(
    tmp_path,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        prune_old_backups,
    )

    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    filenames = [
        "church_city_kids_20261030_090000.db",
        "church_city_kids_20261031_090000.db",
        "church_city_kids_20261101_090000.db",
        "church_city_kids_20269999_999999.db",
        "other_system_20261001_090000.db",
        "important_document.db",
    ]

    for filename in filenames:
        path = backup_directory / filename

        if filename in {
            "church_city_kids_20261030_090000.db",
            "church_city_kids_20261031_090000.db",
            "church_city_kids_20261101_090000.db",
        }:
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "CREATE TABLE children (id INTEGER PRIMARY KEY)"
                )
                connection.commit()
        else:
            path.write_bytes(b"test")

    prune_old_backups(backup_directory, keep_count=2)

    remaining = {
        path.name for path in backup_directory.iterdir()
    }

    assert remaining == {
        "church_city_kids_20261031_090000.db",
        "church_city_kids_20261101_090000.db",
        "church_city_kids_20269999_999999.db",
        "other_system_20261001_090000.db",
        "important_document.db",
    }


@pytest.mark.parametrize("keep_count", [0, -1])
def test_prune_old_backups_rejects_invalid_retention(
    tmp_path,
    keep_count: int,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        prune_old_backups,
    )

    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    backup_path = (
        backup_directory / "church_city_kids_20261101_090000.db"
    )
    backup_path.write_bytes(b"existing backup")

    with pytest.raises(ValueError, match="keep_count must be at least 1"):
        prune_old_backups(backup_directory, keep_count=keep_count)

    assert backup_path.exists()


def test_prune_old_backups_preserves_valid_backup_when_newest_is_corrupted(
    tmp_path,
) -> None:
    from church_city_kids.infrastructure.persistence.database_backup import (
        prune_old_backups,
    )

    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    valid_backup = (
        backup_directory / "church_city_kids_20261031_090000.db"
    )
    corrupted_backup = (
        backup_directory / "church_city_kids_20261101_090000.db"
    )

    with sqlite3.connect(valid_backup) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    corrupted_backup.write_bytes(b"Invalid SQLite database")

    prune_old_backups(backup_directory, keep_count=1)

    assert valid_backup.exists()
    assert corrupted_backup.exists()

    with sqlite3.connect(valid_backup) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

    assert records == [("Maria",)]


def test_run_scheduled_backup_creates_backup_and_applies_retention(
    tmp_path,
) -> None:
    from datetime import datetime

    from church_city_kids.infrastructure.persistence.database_backup import (
        run_scheduled_backup,
    )

    source_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(source_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    first_backup = run_scheduled_backup(
        source_path,
        backup_directory,
        datetime(2026, 11, 1, 9, 0, 0),
        keep_count=1,
    )

    second_backup = run_scheduled_backup(
        source_path,
        backup_directory,
        datetime(2026, 11, 2, 9, 0, 0),
        keep_count=1,
    )

    assert not first_backup.exists()
    assert second_backup.is_file()

    with sqlite3.connect(second_backup) as connection:
        records = connection.execute(
            "SELECT name FROM children"
        ).fetchall()

    assert records == [("Maria",)]

def test_scheduled_backup_failure_preserves_existing_backups(
    tmp_path,
) -> None:
    from datetime import datetime

    from church_city_kids.infrastructure.persistence.database_backup import (
        run_scheduled_backup,
    )

    source_path = tmp_path / "missing.db"
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    existing_backups = [
        backup_directory / "church_city_kids_20261030_090000.db",
        backup_directory / "church_city_kids_20261031_090000.db",
    ]

    for backup_path in existing_backups:
        with sqlite3.connect(backup_path) as connection:
            connection.execute(
                "CREATE TABLE children (id INTEGER PRIMARY KEY)"
            )
            connection.commit()

    with pytest.raises(FileNotFoundError):
        run_scheduled_backup(
            source_path,
            backup_directory,
            datetime(2026, 11, 1, 9, 0, 0),
            keep_count=1,
        )

    assert all(path.exists() for path in existing_backups)
    assert len(list(backup_directory.glob("*.db"))) == 2


def test_timestamped_backup_uses_unique_name_on_collision(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"
    timestamp = datetime(2026, 11, 2, 12, 0, 0)

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY)"
        )

    first_backup = create_timestamped_backup(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=timestamp,
    )

    second_backup = create_timestamped_backup(
        source_path=database_path,
        backup_directory=backup_directory,
        timestamp=timestamp,
    )

    assert first_backup != second_backup
    assert first_backup.exists()
    assert second_backup.exists()

    assert len(list(backup_directory.glob("*.db"))) == 2


def test_prune_old_backups_includes_collision_suffixes(
    tmp_path: Path,
) -> None:
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    oldest = backup_directory / "church_city_kids_20261102_100000.db"
    middle = backup_directory / "church_city_kids_20261102_110000.db"
    newest = backup_directory / "church_city_kids_20261102_120000_1.db"

    for backup_path in (oldest, middle, newest):
        with sqlite3.connect(backup_path) as connection:
            connection.execute(
                "CREATE TABLE children (id INTEGER PRIMARY KEY)"
            )

    prune_old_backups(
        backup_directory=backup_directory,
        keep_count=2,
    )

    assert not oldest.exists()
    assert middle.exists()
    assert newest.exists()
