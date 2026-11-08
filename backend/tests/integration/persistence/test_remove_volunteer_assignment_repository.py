from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session as DbSession

from church_city_kids.application.remove_volunteer_assignment import (
    remove_volunteer_assignment,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import (
    VolunteerAssignmentModel,
    VolunteerModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyRemoveVolunteerAssignmentRepository,
)
from tests.integration.persistence.test_assign_volunteer_repository import (
    seed_service,
)


def test_remove_assignment_deletes_record_but_preserves_volunteer(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        service_id, session_ids, volunteer_ids = seed_service(db)

        assignment = VolunteerAssignmentModel(
            id=uuid4(),
            service_id=service_id,
            session_id=session_ids[0],
            volunteer_id=volunteer_ids[0],
            role="Teacher",
        )
        db.add(assignment)
        db.commit()
        assignment_id = assignment.id

        repository = SqlAlchemyRemoveVolunteerAssignmentRepository(db)
        remove_volunteer_assignment(assignment_id, repository)
        db.commit()

    with DbSession(engine) as db:
        assert db.get(VolunteerAssignmentModel, assignment_id) is None
        assert db.get(VolunteerModel, volunteer_ids[0]) is not None

    engine.dispose()


def test_repository_returns_none_for_unknown_assignment(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with DbSession(engine) as db:
        repository = SqlAlchemyRemoveVolunteerAssignmentRepository(db)

        assert repository.get_by_id(uuid4()) is None

    engine.dispose()
