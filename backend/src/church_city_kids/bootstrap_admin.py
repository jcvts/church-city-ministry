"""Create the initial Church City Kids administrator."""
import getpass
from uuid import uuid4

from sqlalchemy.orm import Session

from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.database_config import (
    get_database_path,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyUserRepository,
)
from church_city_kids.infrastructure.security.config import (
    initialize_jwt_secret_key,
)
from church_city_kids.infrastructure.security.passwords import PasswordHasher


def bootstrap_admin(
    session: Session,
    username: str,
    password: str,
) -> bool:
    """Create the first administrator, if none exists."""
    repository = SqlAlchemyUserRepository(session)

    if any(user.role == "admin" for user in repository.list_all()):
        return False

    username = username.strip()

    if not username:
        raise ValueError("Username cannot be blank")

    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    if not password.strip():
        raise ValueError("Password cannot contain only whitespace")

    if repository.get_by_username(username) is not None:
        raise ValueError("Username already exists")

    administrator = User(
        id=uuid4(),
        username=username,
        password_hash=PasswordHasher().hash(password),
        is_active=True,
        role="admin",
    )

    repository.add(administrator)
    session.commit()

    return True


def main() -> None:
    engine = create_sqlite_engine(get_database_path())

    try:
        with Session(engine) as session:
            repository = SqlAlchemyUserRepository(session)

            if any(user.role == "admin" for user in repository.list_all()):
                created = initialize_jwt_secret_key()

                if created:
                    print("JWT secret key created successfully.")
                else:
                    print("JWT secret key already exists.")

                print("Existing administrator preserved.")
                return

            print("Church City Kids - Initial administrator setup")

            username = input("Administrator username: ").strip()
            password = getpass.getpass("Password (minimum 12 characters): ")
            confirmation = getpass.getpass("Confirm password: ")

            if password != confirmation:
                print("Passwords do not match.")
                return

            try:
                created = bootstrap_admin(session, username, password)
            except ValueError as exc:
                session.rollback()
                print(f"Setup failed: {exc}")
                return

            if created:
                print("Initial administrator created successfully.")
                key_created = initialize_jwt_secret_key()

                if key_created:
                    print("JWT secret key created successfully.")
            
            else:
                print("JWT secret key already exists.")

            print("Existing administrator preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
