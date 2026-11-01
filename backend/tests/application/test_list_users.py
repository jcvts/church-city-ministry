from uuid import uuid4

from church_city_kids.application.list_users import list_users
from church_city_kids.domain.user import User


def test_list_users_returns_all_users() -> None:
    users = [
        User(
            id=uuid4(),
            username="admin.jose",
            password_hash="hash-admin",
            role="admin",
            is_active=True,
        ),
        User(
            id=uuid4(),
            username="volunteer.maria",
            password_hash="hash-volunteer",
            role="volunteer",
            is_active=False,
        ),
    ]

    class FakeUserRepository:
        def list_all(self) -> list[User]:
            return users

    result = list_users(repository=FakeUserRepository())

    assert result == users
    assert len(result) == 2
    assert result[0].role == "admin"
    assert result[1].is_active is False
