from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.models import (
    Base,
    UserModel,
)


def test_user_model_persists_user(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'users.db'}")
    Base.metadata.create_all(engine)

    user_id = uuid4()

    with Session(engine) as session:
        session.add(
            UserModel(
                id=user_id,
                username="maria.silva",
                password_hash="$argon2id$example",
                is_active=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        user = session.get(UserModel, user_id)

        assert user is not None
        assert user.username == "maria.silva"
        assert user.password_hash == "$argon2id$example"
        assert user.is_active is True

    engine.dispose()


def test_user_model_rejects_duplicate_username(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'duplicate_users.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                UserModel(
                    id=uuid4(),
                    username="maria.silva",
                    password_hash="hash-1",
                    is_active=True,
                ),
                UserModel(
                    id=uuid4(),
                    username="maria.silva",
                    password_hash="hash-2",
                    is_active=True,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    engine.dispose()


def test_user_model_rejects_username_with_different_case(
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'case_insensitive_users.db'}"
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                UserModel(
                    id=uuid4(),
                    username="Maria.Silva",
                    password_hash="hash-1",
                    is_active=True,
                ),
                UserModel(
                    id=uuid4(),
                    username="maria.silva",
                    password_hash="hash-2",
                    is_active=True,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    engine.dispose()
