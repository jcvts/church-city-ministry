from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from church_city_kids.application.generate_recurring_services import (
    RecurringServiceSchedule,
    generate_recurring_services,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    RecurringServiceScheduleModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyCreateServiceRepository,
)


def test_recurring_service_is_persisted_without_duplicates(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                RoomModel(
                    id=uuid4(),
                    name="Sala 1",
                    is_active=True,
                    min_age_years=3,
                    max_age_years=5,
                ),
                RoomModel(
                    id=uuid4(),
                    name="Sala 2",
                    is_active=True,
                    min_age_years=6,
                    max_age_years=11,
                ),
                RecurringServiceScheduleModel(
                    name="Culto da manhã",
                    weekday=6,
                    starts_at=time(9, 0),
                    ends_at=time(11, 0),
                    is_active=True,
                ),
            ]
        )
        session.commit()

        schedule = session.scalars(select(RecurringServiceScheduleModel)).one()
        schedule_id = schedule.id

    recurring_schedule = RecurringServiceSchedule(
        id=schedule_id,
        name="Culto da manhã",
        weekday=6,
        starts_at=time(9, 0),
        ends_at=time(11, 0),
    )

    for _ in range(2):
        with Session(engine) as session:
            repository = SqlAlchemyCreateServiceRepository(session)

            generate_recurring_services(
                target_date=date(2026, 11, 8),
                schedules=[recurring_schedule],
                repository=repository,
            )
            session.commit()

    with Session(engine) as session:
        services = session.scalars(select(ServiceModel)).all()
        sessions = session.scalars(select(SessionModel)).all()

        assert len(services) == 1
        assert len(sessions) == 2
        assert services[0].recurring_schedule_id == schedule_id
        assert services[0].starts_at == datetime(2026, 11, 8, 9, 0)
