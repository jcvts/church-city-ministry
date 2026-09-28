from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    ChildGuardianModel,
    ChildModel,
    FamilyModel,
    GuardianModel,
)


def test_people_models_can_be_persisted(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    guardian_id = uuid4()
    child_id = uuid4()

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.flush()

        session.add(
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Test Guardian",
                phone=None,
                is_active=True,
            )
        )
        session.add(
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            )
        )
        session.flush()

        session.add(
            ChildGuardianModel(
                id=uuid4(),
                child_id=child_id,
                guardian_id=guardian_id,
                relationship=None,
                authorized_pickup=True,
            )
        )

        session.commit()

    with Session(engine) as session:
        child = session.get(ChildModel, child_id)
        guardian = session.get(GuardianModel, guardian_id)

        assert child is not None
        assert child.family_id == family_id
        assert child.full_name == "Test Child"
        assert child.birth_date == date(2021, 1, 1)

        assert guardian is not None
        assert guardian.phone is None


def test_child_cannot_reference_nonexistent_family(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            ChildModel(
                id=uuid4(),
                family_id=uuid4(),
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_child_guardian_pair_must_be_unique(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.add(
            ChildModel(
                id=child_id,
                family_id=family_id,
                full_name="Test Child",
                birth_date=date(2021, 1, 1),
                is_active=True,
            )
        )
        session.add(
            GuardianModel(
                id=guardian_id,
                family_id=family_id,
                full_name="Test Guardian",
                phone=None,
                is_active=True,
            )
        )
        session.add_all(
            [
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=child_id,
                    guardian_id=guardian_id,
                    relationship=None,
                    authorized_pickup=True,
                ),
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=child_id,
                    guardian_id=guardian_id,
                    relationship=None,
                    authorized_pickup=True,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()
