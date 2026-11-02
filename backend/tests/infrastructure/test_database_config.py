from pathlib import Path, PureWindowsPath

import pytest

from church_city_kids.infrastructure.persistence.database_config import (
    get_database_path,
)


def test_get_database_path_uses_absolute_environment_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected_path = tmp_path / "church_city_kids.db"

    monkeypatch.setenv(
        "CHURCH_CITY_KIDS_DB_PATH",
        str(expected_path),
    )

    assert get_database_path() == expected_path


def test_get_database_path_rejects_relative_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CHURCH_CITY_KIDS_DB_PATH",
        "church_city_kids.db",
    )

    with pytest.raises(
        ValueError,
        match="Database path must be absolute",
    ):
        get_database_path()


def test_get_database_path_uses_windows_programdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CHURCH_CITY_KIDS_DB_PATH", raising=False)
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")

    database_path = get_database_path()

    assert PureWindowsPath(str(database_path)) == PureWindowsPath(
        r"C:\ProgramData\ChurchCityKids\church_city_kids.db"
    )


def test_get_database_path_uses_home_directory_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("CHURCH_CITY_KIDS_DB_PATH", raising=False)
    monkeypatch.delenv("PROGRAMDATA", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    expected_path = (
        tmp_path / ".church_city_kids" / "church_city_kids.db"
    )

    assert get_database_path() == expected_path
    assert get_database_path().is_absolute()


def test_get_database_path_prefers_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected_path = tmp_path / "custom" / "church_city_kids.db"

    monkeypatch.setenv(
        "CHURCH_CITY_KIDS_DB_PATH",
        str(expected_path),
    )
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")

    assert get_database_path() == expected_path
