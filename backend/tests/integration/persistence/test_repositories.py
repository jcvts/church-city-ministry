from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from church_city_kids.application.check_in import (
    CheckInRequest,
    check_in_child,
)
from church_city_kids.application.check_out import (
    CheckOutRequest,
    check_out_child,
)
from church_city_kids.application.create_service import (
    CreateServiceRequest,
    create_service,
)
from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.domain.errors import ChildAlreadyCheckedInError
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    AttendanceModel,
    ChildModel,
    FamilyModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    ChildGuardianRepository,
    ChildRepository,
    FamilyRepository,
    GuardianRepository,
    SqlAlchemyCheckInRepository,
    SqlAlchemyCheckOutRepository,
    SqlAlchemyCreateServiceRepository,
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


def test_check_in_child_persists_attendance(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

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
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 4, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="OPEN",
            )
        )
        session.commit()

    occurred_at = datetime(2026, 10, 4, 18, 50)

    with Session(engine) as session:
        repository = SqlAlchemyCheckInRepository(session)

        result = check_in_child(
            CheckInRequest(
                child_id=child_id,
                session_id=session_id,
                occurred_at=occurred_at,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, result.attendance_id)

        assert attendance is not None
        assert attendance.child_id == child_id
        assert attendance.session_id == session_id
        assert attendance.checked_in_at == occurred_at
        assert attendance.checked_out_at is None


def test_check_in_child_rejects_existing_active_attendance(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    existing_attendance_id = uuid4()

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

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
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 4, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="OPEN",
            )
        )
        session.flush()

        session.add(
            AttendanceModel(
                id=existing_attendance_id,
                child_id=child_id,
                session_id=session_id,
                checked_in_at=datetime(2026, 10, 4, 18, 30),
                checked_out_at=None,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCheckInRepository(session)

        with pytest.raises(ChildAlreadyCheckedInError):
            check_in_child(
                CheckInRequest(
                    child_id=child_id,
                    session_id=session_id,
                    occurred_at=datetime(2026, 10, 4, 18, 50),
                ),
                repository,
            )

        session.rollback()

    with Session(engine) as session:
        attendances = session.scalars(
            select(AttendanceModel).where(
                AttendanceModel.child_id == child_id,
            )
        ).all()

        assert len(attendances) == 1
        assert attendances[0].id == existing_attendance_id


def test_check_in_child_allows_check_in_after_previous_checkout(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    previous_attendance_id = uuid4()

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

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
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 4, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="OPEN",
            )
        )
        session.flush()

        session.add(
            AttendanceModel(
                id=previous_attendance_id,
                child_id=child_id,
                session_id=session_id,
                checked_in_at=datetime(2026, 10, 4, 18, 20),
                checked_out_at=datetime(2026, 10, 4, 18, 40),
            )
        )
        session.commit()

    second_check_in_at = datetime(2026, 10, 4, 18, 50)

    with Session(engine) as session:
        repository = SqlAlchemyCheckInRepository(session)

        result = check_in_child(
            CheckInRequest(
                child_id=child_id,
                session_id=session_id,
                occurred_at=second_check_in_at,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        attendances = session.scalars(
            select(AttendanceModel)
            .where(AttendanceModel.child_id == child_id)
            .order_by(AttendanceModel.checked_in_at)
        ).all()

        assert len(attendances) == 2

        assert attendances[0].id == previous_attendance_id
        assert attendances[0].checked_out_at == datetime(
            2026, 10, 4, 18, 40
        )

        assert attendances[1].id == result.attendance_id
        assert attendances[1].checked_in_at == second_check_in_at
        assert attendances[1].checked_out_at is None


def test_check_out_child_persists_checkout_time(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()

    checked_in_at = datetime(2026, 10, 4, 18, 30)
    checked_out_at = datetime(2026, 10, 4, 20, 0)

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

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
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 4, 19, 0),
                ends_at=None,
            )
        )

        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="OPEN",
            )
        )
        session.flush()

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
        repository = SqlAlchemyCheckOutRepository(session)

        result = check_out_child(
            CheckOutRequest(
                attendance_id=attendance_id,
                occurred_at=checked_out_at,
            ),
            repository,
        )

        session.commit()

    assert result.attendance_id == attendance_id

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, attendance_id)

        assert attendance is not None
        assert attendance.checked_in_at == checked_in_at
        assert attendance.checked_out_at == checked_out_at


def test_check_out_child_can_be_rolled_back(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()

    checked_in_at = datetime(2026, 10, 4, 18, 30)

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.flush()

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
            ServiceModel(
                id=service_id,
                name="Sunday Service",
                starts_at=datetime(2026, 10, 4, 19, 0),
                ends_at=None,
            )
        )
        session.add(
            RoomModel(
                id=room_id,
                name="Kids Room",
                is_active=True,
            )
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 3-5",
                min_age_years=3,
                max_age_years=5,
                status="OPEN",
            )
        )
        session.flush()

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
        repository = SqlAlchemyCheckOutRepository(session)

        check_out_child(
            CheckOutRequest(
                attendance_id=attendance_id,
                occurred_at=datetime(2026, 10, 4, 20, 0),
            ),
            repository,
        )

        session.rollback()

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, attendance_id)

        assert attendance is not None
        assert attendance.checked_in_at == checked_in_at
        assert attendance.checked_out_at is None


def test_create_service_persists_service(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    starts_at = datetime(2026, 10, 4, 19, 0)
    ends_at = datetime(2026, 10, 4, 21, 0)

    with Session(engine) as session:
        repository = SqlAlchemyCreateServiceRepository(session)

        result = create_service(
            CreateServiceRequest(
                name="Sunday Service",
                starts_at=starts_at,
                ends_at=ends_at,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        service = session.get(ServiceModel, result.service_id)

        assert service is not None
        assert service.name == "Sunday Service"
        assert service.starts_at == starts_at
        assert service.ends_at == ends_at
