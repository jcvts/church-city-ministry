from uuid import uuid4

from church_city_kids.domain.user import User


def test_user_stores_identity_and_credentials() -> None:
    user_id = uuid4()

    user = User(
        id=user_id,
        username="maria.silva",
        password_hash="hashed-password",
        is_active=True,
    )

    assert user.id == user_id
    assert user.username == "maria.silva"
    assert user.password_hash == "hashed-password"
    assert user.is_active is True


def test_new_user_defaults_to_volunteer_role() -> None:
    user = User(
        id=uuid4(),
        username="reception.volunteer",
        password_hash="test-hash",
    )

    assert user.role == "volunteer"


def test_user_can_have_admin_role() -> None:
    user = User(
        id=uuid4(),
        username="reception.admin",
        password_hash="test-hash",
        role="admin",
    )

    assert user.role == "admin"
