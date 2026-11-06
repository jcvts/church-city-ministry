from church_city_kids.infrastructure.security.passwords import (
    PasswordHasher,
)


def test_password_hasher_verifies_correct_password() -> None:
    hasher = PasswordHasher()

    password = "MySecurePassword123!"
    password_hash = hasher.hash(password)

    assert password_hash != password
    assert hasher.verify(password, password_hash) is True


def test_password_hasher_rejects_incorrect_password() -> None:
    hasher = PasswordHasher()

    password_hash = hasher.hash("CorrectPassword123!")

    assert hasher.verify("WrongPassword123!", password_hash) is False


def test_password_hasher_generates_unique_hashes() -> None:
    hasher = PasswordHasher()

    password = "SamePassword123!"

    first_hash = hasher.hash(password)
    second_hash = hasher.hash(password)

    assert first_hash != second_hash
    assert hasher.verify(password, first_hash) is True
    assert hasher.verify(password, second_hash) is True


def test_password_hasher_rejects_invalid_hash() -> None:
    hasher = PasswordHasher()

    assert (
        hasher.verify(
            "MySecurePassword123!",
            "not-a-valid-argon2-hash",
        )
        is False
    )
