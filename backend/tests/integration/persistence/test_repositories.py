from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    FamilyModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    ChildGuardianRepository,
    ChildRepository,
    FamilyRepository,
    GuardianRepository,
    SqlAlchemyRegistrationRepository,
)


def test_child_repository_round_trip(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()

    child = Child(
        family_id=family_id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

        repository = ChildRepository(session)
        repository.add(child)
        session.commit()

    with Session(engine) as session:
        repository = ChildRepository(session)

        loaded_child = repository.get(child.id)

        assert loaded_child == child


def test_child_repository_returns_none_when_child_does_not_exist(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = ChildRepository(session)

        assert repository.get(uuid4()) is None


def test_family_repository_round_trip(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()

    with Session(engine) as session:
        repository = FamilyRepository(session)
        repository.add(family)
        session.commit()

    with Session(engine) as session:
        repository = FamilyRepository(session)

        loaded_family = repository.get(family.id)

        assert loaded_family == family


def test_guardian_repository_round_trip(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()
    guardian = Guardian(
        family_id=family.id,
        full_name="Test Guardian",
        phone="82999999999",
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        repository = GuardianRepository(session)
        repository.add(guardian)
        session.commit()

    with Session(engine) as session:
        repository = GuardianRepository(session)

        loaded_guardian = repository.get(guardian.id)

        assert loaded_guardian == guardian


def test_child_guardian_repository_round_trip(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()

    child = Child(
        family_id=family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=family.id,
        full_name="Test Guardian",
        phone="82999999999",
    )

    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        relationship="Mother",
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(child)
        GuardianRepository(session).add(guardian)
        session.flush()

        repository = ChildGuardianRepository(session)
        repository.add(link)
        session.commit()

    with Session(engine) as session:
        repository = ChildGuardianRepository(session)

        loaded_link = repository.get(link.id)

        assert loaded_link == link


def test_register_child_persists_complete_registration(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    request = RegisterChildRequest(
        child_name="Test Child",
        birth_date=date(2021, 1, 1),
        guardian_name="Test Guardian",
        guardian_phone="82999999999",
        relationship="Mother",
    )

    with Session(engine) as session:
        repository = SqlAlchemyRegistrationRepository(session)

        result = register_child(request, repository)

        session.commit()

    with Session(engine) as session:
        child = ChildRepository(session).get(result.child_id)
        guardian = GuardianRepository(session).get(result.guardian_id)
        family = FamilyRepository(session).get(result.family_id)

        assert family is not None
        assert child is not None
        assert guardian is not None

        assert child.family_id == family.id
        assert guardian.family_id == family.id


def test_registration_can_be_rolled_back_as_single_transaction(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    request = RegisterChildRequest(
        child_name="Test Child",
        birth_date=date(2021, 1, 1),
        guardian_name="Test Guardian",
    )

    with Session(engine) as session:
        repository = SqlAlchemyRegistrationRepository(session)

        result = register_child(request, repository)

        session.rollback()

    with Session(engine) as session:
        assert FamilyRepository(session).get(result.family_id) is None
        assert ChildRepository(session).get(result.child_id) is None
        assert GuardianRepository(session).get(result.guardian_id) is None
