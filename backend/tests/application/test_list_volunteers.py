from uuid import uuid4

from church_city_kids.application.list_volunteers import list_volunteers
from church_city_kids.domain.people import Volunteer


class FakeVolunteerRepository:
    def __init__(self) -> None:
        self.volunteers = [
            Volunteer(
                id=uuid4(),
                full_name="Ana Oliveira",
            ),
            Volunteer(
                id=uuid4(),
                full_name="Carlos Santos",
                is_active=False,
            ),
        ]

    def list_all(self) -> list[Volunteer]:
        return self.volunteers


def test_list_volunteers_returns_all_volunteers() -> None:
    repository = FakeVolunteerRepository()

    result = list_volunteers(repository)

    assert result == repository.volunteers
    assert len(result) == 2
    assert result[1].is_active is False
