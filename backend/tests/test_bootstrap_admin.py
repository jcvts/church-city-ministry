"""Tests for initial administrator bootstrap."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from church_city_kids.application.authenticate_user import (
    authenticate_user,
)
from church_city_kids.bootstrap_admin import bootstrap_admin
from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
)
from church_city_kids.infrastructure.security.passwords import (
    PasswordHasher,
)


def test_bootstrap_creates_initial_admin() -> None:
    session = MagicMock()
    repository = MagicMock()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "church_city_kids.bootstrap_admin.SqlAlchemyUserRepository",
            lambda _: repository,
        )

        repository.list_all.return_value = []
        repository.get_by_username.return_value = None

        created = bootstrap_admin(
            session,
            username="admin",
            password="securepassword123",
        )

    assert created is True
    repository.add.assert_called_once()

    user = repository.add.call_args.args[0]

    assert isinstance(user, User)
    assert user.username == "admin"
    assert user.role == "admin"
    assert user.is_active is True
    assert user.password_hash != "securepassword123"
    session.commit.assert_called_once()


def test_bootstrap_rejects_existing_admin() -> None:
    session = MagicMock()
    repository = MagicMock()

    repository.list_all.return_value = [
        User(
            id=__import__("uuid").uuid4(),
            username="existing_admin",
            password_hash="hashed",
            is_active=False,
            role="admin",
        )
    ]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "church_city_kids.bootstrap_admin.SqlAlchemyUserRepository",
            lambda _: repository,
        )

        created = bootstrap_admin(
            session,
            username="new_admin",
            password="securepassword123",
        )

    assert created is False
    repository.add.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("", "securepassword123"),
        ("admin", "short"),
        ("admin", "            "),
    ],
)
def test_bootstrap_rejects_invalid_credentials(
    username: str,
    password: str,
) -> None:
    session = MagicMock()
    repository = MagicMock()
    repository.list_all.return_value = []
    repository.get_by_username.return_value = None

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "church_city_kids.bootstrap_admin.SqlAlchemyUserRepository",
            lambda _: repository,
        )

        with pytest.raises(ValueError):
            bootstrap_admin(session, username, password)

    repository.add.assert_not_called()
    session.commit.assert_not_called()


def test_bootstrap_rejects_duplicate_username() -> None:
    session = MagicMock()
    repository = MagicMock()

    repository.list_all.return_value = []
    repository.get_by_username.return_value = User(
        id=__import__("uuid").uuid4(),
        username="admin",
        password_hash="hashed",
        role="volunteer",
    )

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "church_city_kids.bootstrap_admin.SqlAlchemyUserRepository",
            lambda _: repository,
        )

        with pytest.raises(ValueError, match="Username already exists"):
            bootstrap_admin(
                session,
                username="admin",
                password="securepassword123",
            )

    repository.add.assert_not_called()
    session.commit.assert_not_called()


def test_bootstrap_admin_sqlite_integration(tmp_path: Path) -> None:

    database_path = tmp_path / "church_city_kids.db"
    engine = create_sqlite_engine(database_path)

    # Create the schema in an isolated test database.
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            assert bootstrap_admin(
                session,
                username="admin",
                password="securepassword123",
            )

        # Reopen the database using a fresh session.
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            authenticated = authenticate_user(
                username="admin",
                password="securepassword123",
                repository=repository,
                password_hasher=PasswordHasher(),
            )

            assert authenticated is not None
            assert authenticated.role == "admin"
            assert authenticated.is_active

            invalid_login = authenticate_user(
                username="admin",
                password="wrongpassword",
                repository=repository,
                password_hasher=PasswordHasher(),
            )

            assert invalid_login is None

            # Bootstrap must not create a second administrator.
            assert not bootstrap_admin(
                session,
                username="another_admin",
                password="anothersecurepassword123",
            )

            assert len(repository.list_all()) == 1
    finally:
        engine.dispose()
