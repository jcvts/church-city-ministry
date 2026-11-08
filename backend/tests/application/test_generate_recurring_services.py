from datetime import date, time

from church_city_kids.application.generate_recurring_services import (
    RecurringServiceSchedule,
    generate_recurring_services,
)
from church_city_kids.domain.scheduling import Room, Service
from tests.application.test_create_service import FakeCreateServiceRepository


class FakeRecurringServiceRepository(FakeCreateServiceRepository):
    def __init__(self, rooms: list[Room]) -> None:
        super().__init__(rooms=rooms)
        self.generated_occurrences: set[tuple[int, date]] = set()

    def occurrence_exists(
        self,
        schedule_id: int,
        target_date: date,
    ) -> bool:
        return (schedule_id, target_date) in self.generated_occurrences

    def add_service(
        self,
        service: Service,
        recurring_schedule_id: int | None = None,
    ) -> None:
        super().add_service(service, recurring_schedule_id)

        if recurring_schedule_id is not None:
            self.generated_occurrences.add(
                (recurring_schedule_id, service.starts_at.date())
            )


def test_generates_two_sunday_services_with_room_sessions() -> None:
    repository = FakeCreateServiceRepository(
        rooms=[
            Room(name="Sala 1", min_age_years=3, max_age_years=5),
            Room(name="Sala 2", min_age_years=6, max_age_years=11),
        ]
    )

    schedules = [
        RecurringServiceSchedule(
            weekday=6,
            starts_at=time(9, 0),
            ends_at=time(11, 0),
        ),
        RecurringServiceSchedule(
            weekday=6,
            starts_at=time(18, 0),
            ends_at=time(20, 0),
        ),
    ]

    generate_recurring_services(
        target_date=date(2026, 11, 8),
        schedules=schedules,
        repository=repository,
    )

    assert len(repository.added_services) == 2
    assert len(repository.added_sessions) == 4

    assert {service.starts_at.hour for service in repository.added_services} == {9, 18}

    assert all(
        service.starts_at.date() == date(2026, 11, 8)
        for service in repository.added_services
    )


def test_generating_same_date_twice_does_not_duplicate_services() -> None:
    repository = FakeRecurringServiceRepository(
        rooms=[
            Room(name="Sala 1", min_age_years=3, max_age_years=5),
            Room(name="Sala 2", min_age_years=6, max_age_years=11),
        ]
    )

    schedules = [
        RecurringServiceSchedule(
            id=1,
            weekday=6,
            starts_at=time(9, 0),
            ends_at=time(11, 0),
        )
    ]

    target_date = date(2026, 11, 8)

    generate_recurring_services(target_date, schedules, repository)
    generate_recurring_services(target_date, schedules, repository)

    assert len(repository.added_services) == 1
    assert len(repository.added_sessions) == 2
