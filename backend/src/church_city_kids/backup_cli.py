
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from church_city_kids.infrastructure.persistence.database_backup import (
    run_scheduled_backup,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Church City Kids SQLite backup."
    )

    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Absolute path to the SQLite database.",
    )

    parser.add_argument(
        "--backup-dir",
        type=Path,
        required=True,
        help="Absolute path to the backup directory.",
    )

    parser.add_argument(
        "--keep-count",
        type=int,
        default=30,
        help="Number of backups to retain (default: 30).",
    )


    args = parser.parse_args()

    if not args.database.is_absolute():
        parser.error("--database must be an absolute path")

    if not args.backup_dir.is_absolute():
        parser.error("--backup-dir must be an absolute path")
    
    if args.keep_count < 1:
        parser.error("--keep-count must be at least 1")
    
    try:
        backup_path = run_scheduled_backup(
            source_path=args.database,
            backup_directory=args.backup_dir,
            timestamp=datetime.now(),
            keep_count=args.keep_count,
        )
    except (OSError, sqlite3.DatabaseError) as exc:
        parser.exit(
            status=1,
            message=f"Backup failed: {exc}\n",
        )

    print(f"Backup created successfully: {backup_path}")


if __name__ == "__main__":
    main()
