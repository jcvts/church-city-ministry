import os


def get_jwt_secret_key() -> str:
    secret_key = os.environ.get("CHURCH_CITY_JWT_SECRET_KEY", "")

    if len(secret_key.encode("utf-8")) < 32:
        raise ValueError(
            "CHURCH_CITY_JWT_SECRET_KEY must be at least 32 bytes"
        )

    return secret_key
