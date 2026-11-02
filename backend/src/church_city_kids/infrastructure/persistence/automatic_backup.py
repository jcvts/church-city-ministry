import logging
import re
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event, Thread

from church_city_kids.infrastructure.persistence.database_backup import (
    run_scheduled_backup,
)

logger = logging.getLogger(__name__)


class AutomaticBackupManager:
    def __init__(
        self,
        database_path: Path,
        backup_directory: Path,
        create_backup: Callable[..., Path] = run_scheduled_backup,
        now: Callable[[], datetime] = datetime.now,
        max_backup_age: timedelta = timedelta(minutes=5),
    ) -> None:
        if max_backup_age <= timedelta(0):
            raise ValueError("max_backup_age must be positive")

        self.database_path = database_path
        self.backup_directory = backup_directory
        self.create_backup = create_backup
        self.now = now
        self.max_backup_age = max_backup_age
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._interval_seconds = 60.0
        self.last_error: str | None = None
    
    def _run_worker(
        self,
        stop_event: Event,
        interval_seconds: float,
    ) -> None:
        while not stop_event.wait(interval_seconds):
            try:
                self.run_backup_if_needed()
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception("Automatic database backup failed")
            else:
                self.last_error = None

    def _has_valid_backup(self, current_time: datetime) -> bool:
        if not self.backup_directory.is_dir():
            return False

        pattern = re.compile(
            rf"{re.escape(self.database_path.stem)}_(\d{{8}}_\d{{6}})(?:_\d+)?\.db"
        )

        for backup_path in self.backup_directory.iterdir():
            if not backup_path.is_file():
                continue

            match = pattern.fullmatch(backup_path.name)
            if match is None:
                continue

            try:
                timestamp = datetime.strptime(
                    match.group(1),
                    "%Y%m%d_%H%M%S",
                )
            except ValueError:
                continue

            age = current_time - timestamp

            if not timedelta(0) <= age <= self.max_backup_age:
                continue

            try:
                with sqlite3.connect(
                    f"file:{backup_path.resolve().as_posix()}?mode=ro",
                    uri=True,
                ) as connection:
                    integrity = connection.execute(
                        "PRAGMA integrity_check"
                    ).fetchone()

                    if integrity == ("ok",):
                        return True

            except sqlite3.DatabaseError:
                continue

        return False

    def run_backup_if_needed(self) -> None:
        current_time = self.now()

        if not self._has_valid_backup(current_time):
            self.create_backup(
                source_path=self.database_path,
                backup_directory=self.backup_directory,
                timestamp=current_time,
            )

    def start(self) -> None:
        if self._thread is not None:
            return

        try:
            self.run_backup_if_needed()
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Initial automatic database backup failed")
        else:
            self.last_error = None

        self._stop_event.clear()

        self._thread = Thread(
            target=self._run_worker,
            kwargs={
                "stop_event": self._stop_event,
                "interval_seconds": self._interval_seconds,
            },
            daemon=True,
            name="church-city-kids-backup",
        )

        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join()
        self._thread = None

        try:
            self.create_backup(
                source_path=self.database_path,
                backup_directory=self.backup_directory,
                timestamp=self.now(),
            )
        except Exception as exc:
            self.last_error = str(exc)
            logger.exception("Final automatic database backup failed")
        else:
            self.last_error = None
