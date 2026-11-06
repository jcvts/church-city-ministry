from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from church_city_kids.domain.people import Volunteer
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import (
    create_sqlite_engine,
)
from church_city_kids.infrastructure.persistence.models import VolunteerModel
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyVolunteerRepository,
)


def test_volunteer_repository_persists_volunteer(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="Maria Oliveira")

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(volunteer)
        session.commit()

    with Session(engine) as session:
        saved = session.get(VolunteerModel, volunteer.id)

        assert saved is not None
        assert saved.full_name == "Maria Oliveira"
        assert saved.is_active is True

    engine.dispose()


def test_volunteer_repository_get_by_id(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="João Silva")

    with Session(engine) as session:
        SqlAlchemyVolunteerRepository(session).add(volunteer)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        result = repository.get_by_id(volunteer.id)

        assert result is not None
        assert result.id == volunteer.id
        assert result.full_name == "João Silva"
        assert result.is_active is True

    engine.dispose()


def test_volunteer_repository_returns_none_for_unknown_id(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)

        assert repository.get_by_id(uuid4()) is None

    engine.dispose()


def test_volunteer_repository_lists_volunteers_alphabetically(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteers = [
        Volunteer(full_name="Carlos"),
        Volunteer(full_name="Ana"),
        Volunteer(full_name="Bruno"),
    ]

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)

        for volunteer in volunteers:
            repository.add(volunteer)

        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        result = repository.list_all()

        assert [volunteer.full_name for volunteer in result] == [
            "Ana",
            "Bruno",
            "Carlos",
        ]

    engine.dispose()


def test_volunteer_repository_lists_inactive_volunteers(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    active = Volunteer(full_name="Active")
    inactive = Volunteer(full_name="Inactive", is_active=False)

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(active)
        repository.add(inactive)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        result = repository.list_all()

        assert len(result) == 2
        assert {volunteer.is_active for volunteer in result} == {
            True,
            False,
        }

    engine.dispose()


def test_volunteer_repository_updates_volunteer(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="Maria Oliveira")

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(volunteer)
        session.commit()

    volunteer.full_name = "Maria Santos"

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.update(volunteer)
        session.commit()

    with Session(engine) as session:
        result = SqlAlchemyVolunteerRepository(session).get_by_id(volunteer.id)

        assert result is not None
        assert result.full_name == "Maria Santos"

    engine.dispose()


def test_volunteer_repository_deactivates_volunteer(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="Maria Oliveira")

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(volunteer)
        session.commit()

    volunteer.deactivate()

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.update(volunteer)
        session.commit()

    with Session(engine) as session:
        result = SqlAlchemyVolunteerRepository(session).get_by_id(volunteer.id)

        assert result is not None
        assert result.is_active is False
        assert result.full_name == "Maria Oliveira"

    engine.dispose()


def test_volunteer_repository_rejects_update_of_unknown_volunteer(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="Unknown")

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)

        try:
            repository.update(volunteer)
        except ValueError as exc:
            assert str(exc) == "Volunteer not found"
        else:
            raise AssertionError("Expected ValueError")

    engine.dispose()


def test_volunteer_repository_updates_name_without_changing_active_status(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(full_name="Maria Oliveira")

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(volunteer)
        session.commit()

    volunteer.full_name = "Maria Santos"

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.update(volunteer)
        session.commit()

    with Session(engine) as session:
        result = SqlAlchemyVolunteerRepository(session).get_by_id(volunteer.id)

        assert result is not None
        assert result.full_name == "Maria Santos"
        assert result.is_active is True

    engine.dispose()


def test_volunteer_repository_updates_inactive_volunteer_name(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    volunteer = Volunteer(
        full_name="Maria Oliveira",
        is_active=False,
    )

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.add(volunteer)
        session.commit()

    volunteer.full_name = "Maria Santos"

    with Session(engine) as session:
        repository = SqlAlchemyVolunteerRepository(session)
        repository.update(volunteer)
        session.commit()

    with Session(engine) as session:
        result = SqlAlchemyVolunteerRepository(session).get_by_id(volunteer.id)

        assert result is not None
        assert result.full_name == "Maria Santos"
        assert result.is_active is False

    engine.dispose()
