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
    engine = create_engine(f"sqlite:///{tmp_path / 'user_repository.db'}")
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
    engine = create_engine(f"sqlite:///{tmp_path / 'unknown_user_repository.db'}")
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
    engine = create_engine(f"sqlite:///{tmp_path / 'username_wildcards.db'}")
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
    engine = create_engine(f"sqlite:///{tmp_path / 'user_creation.db'}")
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
    engine = create_engine(f"sqlite:///{tmp_path / 'user_lookup_by_id.db'}")
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
    engine = create_engine(f"sqlite:///{tmp_path / 'unknown_user_id.db'}")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_id(uuid4())

            assert user is None
    finally:
        engine.dispose()


def test_repository_preserves_admin_role(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'user_admin_role.db'}")
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

    engine = create_engine(f"sqlite:///{tmp_path / 'create_volunteer.db'}")
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


def test_repository_updates_user_active_status(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'user_status_update.db'}")
    Base.metadata.create_all(engine)

    user_id = uuid4()

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=user_id,
                    username="volunteer.maria",
                    password_hash="existing-hash",
                    is_active=True,
                    role="volunteer",
                )
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_id(user_id)
            assert user is not None

            user.is_active = False
            repository.update(user)

            session.commit()

        # Verify persistence using a new database session.
        with Session(engine) as session:
            saved_user = session.get(UserModel, user_id)

            assert saved_user is not None
            assert saved_user.is_active is False
            assert saved_user.username == "volunteer.maria"
            assert saved_user.password_hash == "existing-hash"
            assert saved_user.role == "volunteer"

    finally:
        engine.dispose()


def test_update_user_status_persists_deactivation_and_reactivation(
    tmp_path,
) -> None:
    from church_city_kids.application.update_user_status import (
        update_user_status,
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'user_status_lifecycle.db'}")
    Base.metadata.create_all(engine)

    user_id = uuid4()

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=user_id,
                    username="volunteer.maria",
                    password_hash="existing-hash",
                    is_active=True,
                    role="volunteer",
                )
            )
            session.commit()

        # Deactivate the user.
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            update_user_status(
                user_id=user_id,
                is_active=False,
                repository=repository,
            )

            session.commit()

        # Verify deactivation and reactivate the user.
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            user = repository.get_by_id(user_id)

            assert user is not None
            assert user.is_active is False

            update_user_status(
                user_id=user_id,
                is_active=True,
                repository=repository,
            )

            session.commit()

        # Verify the final persisted state.
        with Session(engine) as session:
            saved_user = session.get(UserModel, user_id)

            assert saved_user is not None
            assert saved_user.is_active is True
            assert saved_user.username == "volunteer.maria"
            assert saved_user.password_hash == "existing-hash"
            assert saved_user.role == "volunteer"

    finally:
        engine.dispose()


def test_repository_lists_all_users_ordered_by_username(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'user_listing.db'}")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            session.add_all(
                [
                    UserModel(
                        id=uuid4(),
                        username="volunteer.zoe",
                        password_hash="hash-zoe",
                        is_active=True,
                        role="volunteer",
                    ),
                    UserModel(
                        id=uuid4(),
                        username="admin.jose",
                        password_hash="hash-jose",
                        is_active=True,
                        role="admin",
                    ),
                    UserModel(
                        id=uuid4(),
                        username="volunteer.maria",
                        password_hash="hash-maria",
                        is_active=False,
                        role="volunteer",
                    ),
                ]
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            users = repository.list_all()

            assert [user.username for user in users] == [
                "admin.jose",
                "volunteer.maria",
                "volunteer.zoe",
            ]

            assert [user.role for user in users] == [
                "admin",
                "volunteer",
                "volunteer",
            ]

            assert [user.is_active for user in users] == [
                True,
                False,
                True,
            ]

            assert all(isinstance(user, User) for user in users)

    finally:
        engine.dispose()


def test_repository_lists_no_users_when_database_is_empty(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'empty_user_listing.db'}")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            users = repository.list_all()

            assert users == []

    finally:
        engine.dispose()


def test_repository_updates_only_user_password_hash(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'user_password_update.db'}")
    Base.metadata.create_all(engine)

    user_id = uuid4()

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=user_id,
                    username="volunteer.maria",
                    password_hash="old-hash",
                    is_active=True,
                    role="volunteer",
                )
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            repository.update_password_hash(
                user_id=user_id,
                password_hash="new-hash",
            )

            session.commit()

        # Verify persistence using a new database session.
        with Session(engine) as session:
            saved_user = session.get(UserModel, user_id)

            assert saved_user is not None
            assert saved_user.password_hash == "new-hash"

            # Other fields must remain unchanged.
            assert saved_user.username == "volunteer.maria"
            assert saved_user.role == "volunteer"
            assert saved_user.is_active is True

    finally:
        engine.dispose()


def test_change_password_persists_new_argon2_hash(tmp_path) -> None:
    from church_city_kids.application.change_password import change_password
    from church_city_kids.infrastructure.security.passwords import (
        PasswordHasher,
    )

    engine = create_engine(f"sqlite:///{tmp_path / 'change_password_integration.db'}")
    Base.metadata.create_all(engine)

    hasher = PasswordHasher()
    user_id = uuid4()

    current_password = "CurrentPassword123!"
    new_password = "NewSecurePassword123!"

    try:
        with Session(engine) as session:
            session.add(
                UserModel(
                    id=user_id,
                    username="volunteer.maria",
                    password_hash=hasher.hash(current_password),
                    is_active=True,
                    role="volunteer",
                )
            )
            session.commit()

        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            change_password(
                user_id=user_id,
                current_password=current_password,
                new_password=new_password,
                repository=repository,
                password_hasher=hasher,
            )

            session.commit()

        # Verify the persisted hash in a separate session.
        with Session(engine) as session:
            saved_user = session.get(UserModel, user_id)

            assert saved_user is not None
            assert saved_user.password_hash != new_password

            assert hasher.verify(
                new_password,
                saved_user.password_hash,
            )

            assert not hasher.verify(
                current_password,
                saved_user.password_hash,
            )

            assert saved_user.username == "volunteer.maria"
            assert saved_user.role == "volunteer"
            assert saved_user.is_active is True

    finally:
        engine.dispose()
