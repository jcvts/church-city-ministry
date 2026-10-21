from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    PagerAssignmentModel,
    PagerModel,
)
from tests.integration.persistence.helpers import (
    create_family_and_service,
)


def test_pager_assignment_can_be_persisted(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    pager_id = uuid4()
    assignment_id = uuid4()

    with Session(engine) as session:
        family_id, service_id = create_family_and_service(session)

        session.add(
            PagerModel(
                id=pager_id,
                code="PAGER-01",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            PagerAssignmentModel(
                id=assignment_id,
                pager_id=pager_id,
                family_id=family_id,
                service_id=service_id,
                assigned_at=datetime(2026, 9, 20, 18, 55),
                released_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        assignment = session.get(PagerAssignmentModel, assignment_id)

        assert assignment is not None
        assert assignment.pager_id == pager_id
        assert assignment.family_id == family_id
        assert assignment.service_id == service_id
        assert assignment.released_at is None


def test_pager_code_must_be_unique(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                PagerModel(
                    id=uuid4(),
                    code="PAGER-01",
                    is_active=True,
                ),
                PagerModel(
                    id=uuid4(),
                    code="PAGER-01",
                    is_active=True,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_pager_release_cannot_be_before_assignment(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    pager_id = uuid4()

    with Session(engine) as session:
        family_id, service_id = create_family_and_service(session)

        session.add(
            PagerModel(
                id=pager_id,
                code="PAGER-01",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            PagerAssignmentModel(
                id=uuid4(),
                pager_id=pager_id,
                family_id=family_id,
                service_id=service_id,
                assigned_at=datetime(2026, 9, 20, 19, 0),
                released_at=datetime(2026, 9, 20, 18, 59),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_pager_cannot_have_two_active_assignments(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    pager_id = uuid4()

    with Session(engine) as session:
        first_family_id, service_id = create_family_and_service(session)
        second_family_id, _ = create_family_and_service(session)

        session.add(
            PagerModel(
                id=pager_id,
                code="PAGER-01",
                is_active=True,
            )
        )
        session.flush()

        session.add_all(
            [
                PagerAssignmentModel(
                    id=uuid4(),
                    pager_id=pager_id,
                    family_id=first_family_id,
                    service_id=service_id,
                    assigned_at=datetime(2026, 9, 20, 18, 55),
                    released_at=None,
                ),
                PagerAssignmentModel(
                    id=uuid4(),
                    pager_id=pager_id,
                    family_id=second_family_id,
                    service_id=service_id,
                    assigned_at=datetime(2026, 9, 20, 18, 56),
                    released_at=None,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_family_cannot_have_two_active_pagers_in_same_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        family_id, service_id = create_family_and_service(session)
        first_pager_id = uuid4()
        second_pager_id = uuid4()



        session.add_all(
            [
                PagerModel(
                    id=first_pager_id,
                    code="PAGER-01",
                    is_active=True,
                ),
                PagerModel(
                    id=second_pager_id,
                    code="PAGER-02",
                    is_active=True,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                PagerAssignmentModel(
                    id=uuid4(),
                    pager_id=first_pager_id,
                    family_id=family_id,
                    service_id=service_id,
                    assigned_at=datetime(2026, 9, 20, 18, 55),
                    released_at=None,
                ),
                PagerAssignmentModel(
                    id=uuid4(),
                    pager_id=second_pager_id,
                    family_id=family_id,
                    service_id=service_id,
                    assigned_at=datetime(2026, 9, 20, 18, 56),
                    released_at=None,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_released_pager_can_be_reassigned_without_losing_history(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    pager_id = uuid4()
    first_assignment_id = uuid4()
    second_assignment_id = uuid4()

    with Session(engine) as session:
        first_family_id, service_id = create_family_and_service(session)
        second_family_id, _ = create_family_and_service(session)

        session.add(
            PagerModel(
                id=pager_id,
                code="PAGER-01",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            PagerAssignmentModel(
                id=first_assignment_id,
                pager_id=pager_id,
                family_id=first_family_id,
                service_id=service_id,
                assigned_at=datetime(2026, 9, 20, 18, 55),
                released_at=datetime(2026, 9, 20, 19, 30),
            )
        )
        session.flush()

        session.add(
            PagerAssignmentModel(
                id=second_assignment_id,
                pager_id=pager_id,
                family_id=second_family_id,
                service_id=service_id,
                assigned_at=datetime(2026, 9, 20, 19, 35),
                released_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        first = session.get(PagerAssignmentModel, first_assignment_id)
        second = session.get(PagerAssignmentModel, second_assignment_id)

        assert first is not None
        assert second is not None

        assert first.released_at == datetime(2026, 9, 20, 19, 30)
        assert second.released_at is None
        assert first.pager_id == second.pager_id
        assert first.family_id != second.family_id
