from uuid import UUID

import pytest

from church_city_kids.application.create_volunteer import (
    CreateVolunteerRequest,
    create_volunteer,
)
from church_city_kids.domain.people import Volunteer


def test_create_volunteer_returns_id_and_persists_volunteer() -> None:
    class FakeVolunteerRepository:
        def __init__(self) -> None:
            self.volunteers: list[Volunteer] = []

        def add(self, volunteer: Volunteer) -> None:
            self.volunteers.append(volunteer)

    repository = FakeVolunteerRepository()

    volunteer_id = create_volunteer(
        CreateVolunteerRequest(full_name="Maria Oliveira"),
        repository,
    )

    assert isinstance(volunteer_id, UUID)
    assert len(repository.volunteers) == 1

    volunteer = repository.volunteers[0]

    assert volunteer.id == volunteer_id
    assert volunteer.full_name == "Maria Oliveira"
    assert volunteer.is_active is True


def test_create_volunteer_normalizes_name() -> None:
    class FakeVolunteerRepository:
        def __init__(self) -> None:
            self.volunteers: list[Volunteer] = []

        def add(self, volunteer: Volunteer) -> None:
            self.volunteers.append(volunteer)

    repository = FakeVolunteerRepository()

    create_volunteer(
        CreateVolunteerRequest(full_name="  Maria Oliveira  "),
        repository,
    )

    assert repository.volunteers[0].full_name == "Maria Oliveira"


@pytest.mark.parametrize(
    "full_name",
    ["", "   ", "\t", "\n"],
)
def test_create_volunteer_rejects_blank_name(
    full_name: str,
) -> None:
    class FakeVolunteerRepository:
        def add(self, volunteer: Volunteer) -> None:
            raise AssertionError("Repository should not be called")

    with pytest.raises(
        ValueError,
        match="Volunteer name cannot be blank",
    ):
        create_volunteer(
            CreateVolunteerRequest(full_name=full_name),
            FakeVolunteerRepository(),
        )
