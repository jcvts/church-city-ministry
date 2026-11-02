import os
from pathlib import Path, PureWindowsPath


def get_database_path() -> Path:
    configured_path = os.environ.get("CHURCH_CITY_KIDS_DB_PATH")

    if configured_path is not None:
        database_path = Path(configured_path)

        if not database_path.is_absolute():
            raise ValueError("Database path must be absolute")

        return database_path

    programdata = os.environ.get("PROGRAMDATA")

    if programdata:
        windows_path = (
            PureWindowsPath(programdata)
            / "ChurchCityKids"
            / "church_city_kids.db"
        )
        return Path(str(windows_path))

    return Path.home() / ".church_city_kids" / "church_city_kids.db"
