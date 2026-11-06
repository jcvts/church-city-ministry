import os
import sqlite3
import subprocess
import sys


def test_backup_cli_rejects_relative_database_path(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            "church_city_kids.db",
            "--backup-dir",
            str(tmp_path / "backups"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "absolute" in result.stderr.lower()


def test_backup_cli_creates_database_backup(tmp_path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )
        connection.commit()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    backups = list(backup_directory.glob("church_city_kids_*.db"))
    assert len(backups) == 1

    with sqlite3.connect(backups[0]) as connection:
        records = connection.execute("SELECT name FROM children").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()

    assert records == [("Maria",)]
    assert integrity == ("ok",)


def test_backup_cli_rejects_missing_database(tmp_path) -> None:
    database_path = tmp_path / "missing.db"
    backup_directory = tmp_path / "backups"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "database not found" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()

    assert not database_path.exists()
    assert not backup_directory.exists()


def test_backup_cli_rejects_relative_backup_directory(tmp_path) -> None:
    database_path = tmp_path / "church_city_kids.db"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            "backups",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--backup-dir must be an absolute path" in result.stderr
    assert "traceback" not in result.stderr.lower()
    assert not database_path.exists()


def test_backup_cli_accepts_custom_retention_count(tmp_path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    backup_directory.mkdir()

    for index in range(3):
        old_backup = backup_directory / (
            f"church_city_kids_2026010{index + 1}_120000.db"
        )
        with sqlite3.connect(old_backup) as connection:
            connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
            "--keep-count",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    backups = list(backup_directory.glob("church_city_kids_*.db"))
    assert len(backups) == 2


def test_backup_cli_rejects_invalid_retention_count(tmp_path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
            "--keep-count",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--keep-count must be at least 1" in result.stderr
    assert "traceback" not in result.stderr.lower()

    assert not database_path.exists()
    assert not backup_directory.exists()


def test_backup_cli_rejects_corrupted_database(tmp_path) -> None:
    database_path = tmp_path / "church_city_kids.db"
    backup_directory = tmp_path / "backups"

    database_path.write_bytes(b"This is not a SQLite database")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "backup failed" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()

    assert database_path.read_bytes() == b"This is not a SQLite database"

    if backup_directory.exists():
        assert list(backup_directory.iterdir()) == []


def test_backup_cli_uses_configured_database_by_default(
    tmp_path,
) -> None:
    database_path = tmp_path / "configured.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE children (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO children (name) VALUES (?)",
            ("Maria",),
        )

    environment = os.environ.copy()
    environment["CHURCH_CITY_KIDS_DB_PATH"] = str(database_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--backup-dir",
            str(backup_directory),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print(
        "Backup directory contents:",
        list(backup_directory.iterdir())
        if backup_directory.exists()
        else "Directory does not exist",
    )

    backups = list(backup_directory.glob("configured_*.db"))
    assert len(backups) == 1

    with sqlite3.connect(backups[0]) as connection:
        records = connection.execute("SELECT name FROM children").fetchall()

    assert records == [("Maria",)]


def test_backup_cli_applies_retention_to_custom_database_name(
    tmp_path,
) -> None:
    database_path = tmp_path / "configured.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    backup_directory.mkdir()

    for index in range(3):
        old_backup = backup_directory / (f"configured_2026010{index + 1}_120000.db")
        with sqlite3.connect(old_backup) as connection:
            connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
            "--keep-count",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    backups = list(backup_directory.glob("configured_*.db"))
    assert len(backups) == 2


def test_backup_cli_retention_preserves_other_database_backups(
    tmp_path,
) -> None:
    database_path = tmp_path / "configured.db"
    backup_directory = tmp_path / "backups"

    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    backup_directory.mkdir()

    for index in range(3):
        timestamp = f"2026010{index + 1}_120000"

        for prefix in ("configured", "other_database"):
            backup_path = backup_directory / (f"{prefix}_{timestamp}.db")

            with sqlite3.connect(backup_path) as connection:
                connection.execute("CREATE TABLE children (id INTEGER PRIMARY KEY)")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "church_city_kids.backup_cli",
            "--database",
            str(database_path),
            "--backup-dir",
            str(backup_directory),
            "--keep-count",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    configured_backups = list(backup_directory.glob("configured_*.db"))
    other_backups = list(backup_directory.glob("other_database_*.db"))

    assert len(configured_backups) == 2
    assert len(other_backups) == 3
