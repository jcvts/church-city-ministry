from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


class JwtTokenService:
    def __init__(
        self,
        secret_key: str,
        access_token_ttl: timedelta,
    ) -> None:
        if len(secret_key.encode("utf-8")) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 bytes"
            )

        if access_token_ttl <= timedelta(0):
            raise ValueError("Access token TTL must be positive")

        self._secret_key = secret_key
        self._access_token_ttl = access_token_ttl

    def create_access_token(self, user_id: UUID) -> str:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self._access_token_ttl

        payload = {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            self._secret_key,
            algorithm="HS256",
        )
    
    def decode_access_token(self, token: str) -> UUID:
        payload = jwt.decode(
            token,
            self._secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )

        try:
            return UUID(payload["sub"])
        except (ValueError, TypeError, AttributeError) as exc:
            raise jwt.InvalidTokenError(
                "Invalid user identifier"
            ) from exc
