from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Protocol

from church_city_kids.application.create_service import (
    CreateServiceRepository,
    CreateServiceRequest,
    create_service,
)


@dataclass(frozen=True)
class RecurringServiceSchedule:
    weekday: int
    starts_at: time
    ends_at: time
    name: str | None = None
    id: int | None = None


class RecurringServiceRepository(CreateServiceRepository, Protocol):
    def occurrence_exists(
        self,
        schedule_id: int,
        target_date: date,
    ) -> bool: ...


def generate_recurring_services(
    target_date: date,
    schedules: list[RecurringServiceSchedule],
    repository: RecurringServiceRepository,
) -> None:
    for schedule in schedules:
        if schedule.weekday != target_date.weekday():
            continue

        if schedule.id is not None and repository.occurrence_exists(
            schedule.id,
            target_date,
        ):
            continue

        starts_at = datetime.combine(target_date, schedule.starts_at)
        ends_at = datetime.combine(target_date, schedule.ends_at)

        create_service(
            CreateServiceRequest(
                name=schedule.name or f"Culto {target_date:%d/%m/%Y}",
                starts_at=starts_at,
                ends_at=ends_at,
                recurring_schedule_id=schedule.id,
            ),
            repository,
        )
