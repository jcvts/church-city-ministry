from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import AttendanceModel
from tests.integration.persistence.helpers import (
    create_attendance_dependencies,
)


def test_attendance_can_be_persisted(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    attendance_id = uuid4()
    checked_in_at = datetime(2026, 9, 20, 18, 50)

    with Session(engine) as session:
        child_id, session_id = create_attendance_dependencies(session)

        session.add(
            AttendanceModel(
                id=attendance_id,
                child_id=child_id,
                session_id=session_id,
                checked_in_at=checked_in_at,
                checked_out_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, attendance_id)

        assert attendance is not None
        assert attendance.child_id == child_id
        assert attendance.session_id == session_id
        assert attendance.checked_in_at == checked_in_at
        assert attendance.checked_out_at is None


def test_checkout_cannot_be_before_checkin(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        child_id, session_id = create_attendance_dependencies(session)

        session.add(
            AttendanceModel(
                id=uuid4(),
                child_id=child_id,
                session_id=session_id,
                checked_in_at=datetime(2026, 9, 20, 19, 0),
                checked_out_at=datetime(2026, 9, 20, 18, 59),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_attendance_requires_existing_child_and_session(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            AttendanceModel(
                id=uuid4(),
                child_id=uuid4(),
                session_id=uuid4(),
                checked_in_at=datetime(2026, 9, 20, 19, 0),
                checked_out_at=None,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
