from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from church_city_kids.infrastructure.security.jwt_tokens import (
    JwtTokenService,
)


def test_create_access_token_contains_user_id_and_expiration() -> None:
    secret_key = "test-secret-key-only-for-unit-tests"
    user_id = uuid4()

    service = JwtTokenService(
        secret_key=secret_key,
        access_token_ttl=timedelta(minutes=30),
    )

    token = service.create_access_token(user_id)

    payload = jwt.decode(
        token,
        secret_key,
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp"]},
    )

    assert payload["sub"] == str(user_id)
    assert payload["exp"] > payload["iat"]
    assert payload["exp"] - payload["iat"] == 1800


def test_decode_access_token_returns_user_id() -> None:
    user_id = uuid4()

    service = JwtTokenService(
        secret_key="test-secret-key-only-for-unit-tests",
        access_token_ttl=timedelta(minutes=30),
    )

    token = service.create_access_token(user_id)

    decoded_user_id = service.decode_access_token(token)

    assert decoded_user_id == user_id


def test_decode_access_token_rejects_expired_token() -> None:
    secret_key = "test-secret-key-only-for-unit-tests"
    user_id = uuid4()

    service = JwtTokenService(
        secret_key=secret_key,
        access_token_ttl=timedelta(minutes=30),
    )

    expired_at = datetime.now(UTC) - timedelta(minutes=1)

    token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": expired_at - timedelta(minutes=30),
            "exp": expired_at,
        },
        secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        service.decode_access_token(token)


def test_decode_access_token_rejects_invalid_signature() -> None:
    service = JwtTokenService(
        secret_key="correct-secret-key-for-testing-123456789",
        access_token_ttl=timedelta(minutes=30),
    )

    attacker_service = JwtTokenService(
        secret_key="different-secret-key-for-testing-987654321",
        access_token_ttl=timedelta(minutes=30),
    )

    forged_token = attacker_service.create_access_token(uuid4())

    with pytest.raises(jwt.InvalidSignatureError):
        service.decode_access_token(forged_token)


def test_decode_access_token_rejects_invalid_user_id() -> None:
    secret_key = "test-secret-key-only-for-unit-tests"
    service = JwtTokenService(
        secret_key=secret_key,
        access_token_ttl=timedelta(minutes=30),
    )

    issued_at = datetime.now(UTC)

    token = jwt.encode(
        {
            "sub": "not-a-valid-uuid",
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=30),
        },
        secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        service.decode_access_token(token)


def test_jwt_token_service_rejects_short_secret_key() -> None:
    with pytest.raises(
        ValueError,
        match="JWT secret key must be at least 32 bytes",
    ):
        JwtTokenService(
            secret_key="short-secret",
            access_token_ttl=timedelta(minutes=30),
        )
