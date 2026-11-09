import os
from pathlib import Path

import pytest

from church_city_kids.infrastructure.security import config


@pytest.fixture
def secret_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    path = tmp_path / "jwt_secret.key"

    monkeypatch.delenv("CHURCH_CITY_JWT_SECRET_KEY", raising=False)
    monkeypatch.setattr(config, "get_jwt_secret_path", lambda: path)

    return path


def test_initialization_creates_valid_key(secret_path: Path) -> None:
    assert config.initialize_jwt_secret_key() is True

    assert secret_path.is_file()
    assert config.get_jwt_secret_key() == secret_path.read_text(
        encoding="utf-8"
    )
    assert len(config.get_jwt_secret_key().encode("utf-8")) >= 32


def test_initialization_preserves_existing_key(secret_path: Path) -> None:
    assert config.initialize_jwt_secret_key() is True

    original_key = secret_path.read_bytes()

    assert config.initialize_jwt_secret_key() is False
    assert secret_path.read_bytes() == original_key


def test_environment_variable_takes_priority(
    secret_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config.initialize_jwt_secret_key()

    monkeypatch.setenv("CHURCH_CITY_JWT_SECRET_KEY", "a" * 32)

    assert config.get_jwt_secret_key() == "a" * 32


def test_missing_key_is_rejected(secret_path: Path) -> None:
    assert not secret_path.exists()

    with pytest.raises(ValueError, match="not configured"):
        config.get_jwt_secret_key()


def test_invalid_existing_key_is_rejected(secret_path: Path) -> None:
    secret_path.write_text("short", encoding="utf-8")

    with pytest.raises(ValueError, match="at least 32 bytes"):
        config.initialize_jwt_secret_key()

    assert secret_path.read_text(encoding="utf-8") == "short"


def test_invalid_environment_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHURCH_CITY_JWT_SECRET_KEY", "short")

    with pytest.raises(ValueError, match="at least 32 bytes"):
        config.get_jwt_secret_key()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_created_key_has_restricted_permissions(secret_path: Path) -> None:
    config.initialize_jwt_secret_key()

    assert secret_path.stat().st_mode & 0o777 == 0o600


def test_failed_write_removes_incomplete_key(
    secret_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_fsync = os.fsync

    def failing_fsync(fd: int) -> None:
        raise OSError("Simulated disk write failure")

    monkeypatch.setattr(os, "fsync", failing_fsync)

    with pytest.raises(OSError, match="Simulated disk write failure"):
        config.initialize_jwt_secret_key()

    assert not secret_path.exists()

    monkeypatch.setattr(os, "fsync", original_fsync)

    assert config.initialize_jwt_secret_key() is True
    assert secret_path.is_file()
