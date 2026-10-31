from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
)
from church_city_kids.infrastructure.security.config import (
    get_jwt_secret_key,
)
from church_city_kids.infrastructure.security.jwt_tokens import (
    JwtTokenService,
)

engine = create_sqlite_engine(Path("church_city_kids.db"))
bearer_scheme = HTTPBearer(auto_error=True)


def get_jwt_token_service() -> JwtTokenService:
    return JwtTokenService(
        secret_key=get_jwt_secret_key(),
        access_token_ttl=timedelta(minutes=30),
    )


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def require_bearer_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db_session: Annotated[Session, Depends(get_db_session)],
    token_service: Annotated[
        JwtTokenService,
        Depends(get_jwt_token_service),
    ],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = token_service.decode_access_token(
            credentials.credentials
        )
    except jwt.InvalidTokenError:
        raise unauthorized from None

    repository = SqlAlchemyUserRepository(db_session)
    user = repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_admin(
    user: Annotated[User, Depends(require_bearer_token)],
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
