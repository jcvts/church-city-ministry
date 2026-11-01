import os
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path


def backup_sqlite_database(source_path: Path, backup_path: Path) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(f"Database not found: {source_path}")

    if backup_path.exists():
        raise FileExistsError(
            f"Backup destination already exists: {backup_path}"
        )

    backup_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=".backup_",
        suffix=".db",
        dir=backup_path.parent,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)

    try:
        with sqlite3.connect(source_path) as source:
            with sqlite3.connect(temporary_path) as destination:
                source.backup(destination)

                integrity = destination.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if integrity != ("ok",):
                    raise sqlite3.DatabaseError(
                        "Backup failed integrity check"
                    )

        # Create the final backup only if the destination does not exist.
        # Hard linking avoids replacing an existing file.
        os.link(temporary_path, backup_path)

    finally:
        temporary_path.unlink(missing_ok=True)



def restore_sqlite_database(backup_path: Path, restore_path: Path) -> None:
    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    if restore_path.exists():
        raise FileExistsError(
            f"Restore destination already exists: {restore_path}"
        )

    restore_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=".restore_",
        suffix=".db",
        dir=restore_path.parent,
    )
    os.close(fd)
    temporary_path = Path(temporary_name)

    try:
        with sqlite3.connect(backup_path) as source:
            with sqlite3.connect(temporary_path) as destination:
                source.backup(destination)

                integrity = destination.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if integrity != ("ok",):
                    raise sqlite3.DatabaseError(
                        "Restored database failed integrity check"
                    )

        if restore_path.exists():
            raise FileExistsError(
                f"Restore destination already exists: {restore_path}"
            )

        temporary_path.rename(restore_path)

    finally:
        temporary_path.unlink(missing_ok=True)


def create_timestamped_backup(
    source_path: Path,
    backup_directory: Path,
    timestamp: datetime,
) -> Path:
    filename = (
        f"{source_path.stem}_"
        f"{timestamp.strftime('%Y%m%d_%H%M%S')}.db"
    )

    backup_path = backup_directory / filename

    backup_sqlite_database(source_path, backup_path)

    return backup_path


def prune_old_backups(
    backup_directory: Path,
    keep_count: int = 30,
) -> None:
    if keep_count < 1:
        raise ValueError("keep_count must be at least 1")

    if not backup_directory.exists():
        return

    pattern = re.compile(
        r"church_city_kids_(\d{8}_\d{6})\.db"
    )

    backups = []

    for path in backup_directory.iterdir():
        if not path.is_file():
            continue

        match = pattern.fullmatch(path.name)

        if match is None:
            continue

        try:
            timestamp = datetime.strptime(
                match.group(1),
                "%Y%m%d_%H%M%S",
            )
        except ValueError:
            continue

        # Require the canonical timestamp representation.
        if timestamp.strftime("%Y%m%d_%H%M%S") != match.group(1):
            continue

        try:
            with sqlite3.connect(
                f"file:{path.resolve().as_posix()}?mode=ro", uri=True
            ) as connection:
                integrity = connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()

                if integrity != ("ok",):
                    continue

        except sqlite3.DatabaseError:
            continue

        backups.append((timestamp, path))


    backups.sort(key=lambda item: item[0], reverse=True)

    for _, old_backup in backups[keep_count:]:
        old_backup.unlink()


def run_scheduled_backup(
    source_path: Path,
    backup_directory: Path,
    timestamp: datetime,
    keep_count: int = 30,
) -> Path:
    if keep_count < 1:
        raise ValueError("keep_count must be at least 1")

    backup_path = create_timestamped_backup(
        source_path,
        backup_directory,
        timestamp,
    )

    prune_old_backups(
        backup_directory,
        keep_count=keep_count,
    )

    return backup_path
