import os
import secrets
from pathlib import Path

from church_city_kids.infrastructure.persistence.database_config import (
    get_database_path,
)


def get_jwt_secret_path() -> Path:
    return get_database_path().parent / "jwt_secret.key"


def get_jwt_secret_key() -> str:
    configured_key = os.environ.get("CHURCH_CITY_JWT_SECRET_KEY")

    if configured_key is not None:
        secret_key = configured_key
    else:
        secret_path = get_jwt_secret_path()

        try:
            secret_key = secret_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            raise ValueError(
                "JWT secret key not configured. "
                "Run the initial setup before starting the application."
            ) from None

    if len(secret_key.encode("utf-8")) < 32:
        raise ValueError("JWT secret key must be at least 32 bytes")

    return secret_key


def initialize_jwt_secret_key() -> bool:
    """Create a persistent JWT key only if one does not exist."""
    secret_path = get_jwt_secret_path()

    if secret_path.exists():
        get_jwt_secret_key_from_file(secret_path)
        return False

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    secret_key = secrets.token_urlsafe(48)

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    try:
        fd = os.open(secret_path, flags, 0o600)
    except FileExistsError:
        get_jwt_secret_key_from_file(secret_path)
        return False

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as secret_file:
            secret_file.write(secret_key)
            secret_file.flush()
            os.fsync(secret_file.fileno())
    except Exception:
        secret_path.unlink(missing_ok=True)
        raise

    return True


def get_jwt_secret_key_from_file(secret_path: Path) -> str:
    """Read and validate the persistent JWT key."""
    secret_key = secret_path.read_text(encoding="utf-8").strip()

    if len(secret_key.encode("utf-8")) < 32:
        raise ValueError("JWT secret key must be at least 32 bytes")

    return secret_key
