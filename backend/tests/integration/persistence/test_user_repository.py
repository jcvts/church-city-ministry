from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.models import UserModel
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
)


def test_repository_finds_user_by_username_case_insensitively(
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'user_repository.db'}"
    )
    Base.metadata.create_all(engine)

    user_id = uuid4()

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=user_id,
                    username="Reception.Admin",
                    password_hash="test-hash",
                    is_active=True,
                )
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_username("reception.admin")

            assert user is not None
            assert user.id == user_id
            assert user.username == "Reception.Admin"
            assert user.password_hash == "test-hash"
            assert user.is_active is True
    finally:
        engine.dispose()


def test_repository_returns_none_for_unknown_username(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'unknown_user_repository.db'}"
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_username("nonexistent.user")

            assert user is None
    finally:
        engine.dispose()


def test_repository_treats_username_wildcards_as_literals(
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'username_wildcards.db'}"
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=uuid4(),
                    username="admin123",
                    password_hash="test-hash",
                    is_active=True,
                )
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            assert repository.get_by_username("admin%") is None
            assert repository.get_by_username("admin_23") is None
    finally:
        engine.dispose()


def test_repository_adds_user(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'user_creation.db'}"
    )
    Base.metadata.create_all(engine)

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash="argon2-hash-placeholder",
        is_active=True,
    )

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)
            repository.add(user)
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)
            saved_user = repository.get_by_username("reception.admin")

            assert saved_user == user
    finally:
        engine.dispose()


def test_repository_finds_user_by_id(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'user_lookup_by_id.db'}"
    )
    Base.metadata.create_all(engine)

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash="test-hash",
        is_active=True,
    )

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)
            repository.add(user)
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            found_user = repository.get_by_id(user.id)

            assert found_user == user
    finally:
        engine.dispose()


def test_repository_returns_none_for_unknown_user_id(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'unknown_user_id.db'}"
    )
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_id(uuid4())

            assert user is None
    finally:
        engine.dispose()


def test_repository_preserves_admin_role(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'user_admin_role.db'}"
    )
    Base.metadata.create_all(engine)

    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash="test-hash",
        role="admin",
    )

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)
            repository.add(user)
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            saved_user = repository.get_by_id(user.id)

            assert saved_user is not None
            assert saved_user.role == "admin"
            assert saved_user == user
    finally:
        engine.dispose()


def test_create_user_persists_volunteer_with_hashed_password(
    tmp_path,
) -> None:
    from church_city_kids.application.create_user import (
        CreateUserRequest,
        create_user,
    )
    from church_city_kids.infrastructure.security.passwords import (
        PasswordHasher,
    )

    engine = create_engine(
        f"sqlite:///{tmp_path / 'create_volunteer.db'}"
    )
    Base.metadata.create_all(engine)

    password_hasher = PasswordHasher()

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user_id = create_user(
                CreateUserRequest(
                    username="volunteer.maria",
                    password="SecurePassword123!",
                ),
                repository,
                password_hasher,
            )

            session.commit()

        # Open a new session to verify actual database persistence.
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            saved_user = repository.get_by_id(user_id)

            assert saved_user is not None
            assert saved_user.username == "volunteer.maria"
            assert saved_user.role == "volunteer"
            assert saved_user.is_active is True
            assert saved_user.password_hash != "SecurePassword123!"
            assert password_hasher.verify(
                "SecurePassword123!",
                saved_user.password_hash,
            )
    finally:
        engine.dispose()
