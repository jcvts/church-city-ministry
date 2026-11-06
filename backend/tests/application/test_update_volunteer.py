from uuid import uuid4

import pytest

from church_city_kids.application.update_volunteer import (
    UpdateVolunteerRequest,
    VolunteerNotFoundError,
    update_volunteer,
)
from church_city_kids.domain.people import Volunteer


class FakeVolunteerRepository:
    def __init__(self, volunteer: Volunteer | None = None) -> None:
        self.volunteer = volunteer
        self.updated_volunteers: list[Volunteer] = []

    def get_by_id(self, volunteer_id):
        if self.volunteer is None:
            return None

        if self.volunteer.id != volunteer_id:
            return None

        return self.volunteer

    def update(self, volunteer: Volunteer) -> None:
        self.updated_volunteers.append(volunteer)


def test_update_volunteer_changes_name() -> None:
    volunteer = Volunteer(full_name="John Smith")
    repository = FakeVolunteerRepository(volunteer)

    update_volunteer(
        UpdateVolunteerRequest(
            volunteer_id=volunteer.id,
            full_name="Jane Smith",
        ),
        repository,
    )

    assert volunteer.full_name == "Jane Smith"
    assert repository.updated_volunteers == [volunteer]


def test_update_volunteer_strips_name_whitespace() -> None:
    volunteer = Volunteer(full_name="John Smith")
    repository = FakeVolunteerRepository(volunteer)

    update_volunteer(
        UpdateVolunteerRequest(
            volunteer_id=volunteer.id,
            full_name="  Jane Smith  ",
        ),
        repository,
    )

    assert volunteer.full_name == "Jane Smith"


@pytest.mark.parametrize("name", ["", "   ", "\t", "\n"])
def test_update_volunteer_rejects_blank_name(name: str) -> None:
    volunteer = Volunteer(full_name="John Smith")
    repository = FakeVolunteerRepository(volunteer)

    with pytest.raises(ValueError, match="cannot be blank"):
        update_volunteer(
            UpdateVolunteerRequest(
                volunteer_id=volunteer.id,
                full_name=name,
            ),
            repository,
        )

    assert volunteer.full_name == "John Smith"
    assert repository.updated_volunteers == []


def test_update_volunteer_rejects_non_string_name() -> None:
    volunteer = Volunteer(full_name="John Smith")
    repository = FakeVolunteerRepository(volunteer)

    with pytest.raises(ValueError, match="Invalid volunteer name"):
        update_volunteer(
            UpdateVolunteerRequest(
                volunteer_id=volunteer.id,
                full_name=123,  # type: ignore[arg-type]
            ),
            repository,
        )

    assert volunteer.full_name == "John Smith"
    assert repository.updated_volunteers == []


def test_update_volunteer_rejects_empty_request() -> None:
    volunteer = Volunteer(full_name="John Smith")
    repository = FakeVolunteerRepository(volunteer)

    with pytest.raises(ValueError, match="At least one field"):
        update_volunteer(
            UpdateVolunteerRequest(volunteer_id=volunteer.id),
            repository,
        )

    assert volunteer.full_name == "John Smith"
    assert repository.updated_volunteers == []


def test_update_volunteer_rejects_unknown_volunteer() -> None:
    repository = FakeVolunteerRepository()

    with pytest.raises(VolunteerNotFoundError):
        update_volunteer(
            UpdateVolunteerRequest(
                volunteer_id=uuid4(),
                full_name="Jane Smith",
            ),
            repository,
        )

    assert repository.updated_volunteers == []


def test_update_volunteer_preserves_inactive_status() -> None:
    volunteer = Volunteer(
        full_name="John Smith",
        is_active=False,
    )
    repository = FakeVolunteerRepository(volunteer)

    update_volunteer(
        UpdateVolunteerRequest(
            volunteer_id=volunteer.id,
            full_name="Jane Smith",
        ),
        repository,
    )

    assert volunteer.full_name == "Jane Smith"
    assert volunteer.is_active is False
    assert repository.updated_volunteers == [volunteer]
