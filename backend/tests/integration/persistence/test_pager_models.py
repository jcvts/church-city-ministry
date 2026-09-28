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
from tests.integration.persistence.helpers import create_attendance


def test_pager_assignment_can_be_persisted(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    pager_id = uuid4()
    assignment_id = uuid4()

    with Session(engine) as session:
        attendance_id = create_attendance(session)

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
                attendance_id=attendance_id,
                assigned_at=datetime(2026, 9, 20, 18, 55),
                released_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        assignment = session.get(
            PagerAssignmentModel,
            assignment_id,
        )

        assert assignment is not None
        assert assignment.pager_id == pager_id
        assert assignment.attendance_id == attendance_id
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
        attendance_id = create_attendance(session)

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
                attendance_id=attendance_id,
                assigned_at=datetime(2026, 9, 20, 19, 0),
                released_at=datetime(2026, 9, 20, 18, 59),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
