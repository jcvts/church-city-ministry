from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from church_city_kids.application.add_child_guardian import (
    AddChildGuardianRequest,
    add_child_guardian,
)
from church_city_kids.application.check_in import (
    CheckInRequest,
    check_in_child,
)
from church_city_kids.application.check_out import (
    CheckOutRequest,
    check_out_child,
)
from church_city_kids.application.create_room import (
    CreateRoomRequest,
    create_room,
)
from church_city_kids.application.create_service import (
    CreateServiceRequest,
    create_service,
)
from church_city_kids.application.get_child_details import get_child_details
from church_city_kids.application.list_children import list_children
from church_city_kids.application.list_rooms import list_rooms
from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.application.remove_child_guardian import (
    RemoveChildGuardianRequest,
    remove_child_guardian,
)
from church_city_kids.application.update_child import (
    UpdateChildRequest,
    update_child,
)
from church_city_kids.application.update_child_guardian import (
    UpdateChildGuardianRequest,
    update_child_guardian,
)
from church_city_kids.domain.errors import (
    ChildAlreadyCheckedInError,
    DuplicateChildGuardianError,
    GuardianNotAuthorizedForPickupError,
)
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)
from church_city_kids.domain.scheduling import Room
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.database import create_sqlite_engine
from church_city_kids.infrastructure.persistence.models import (
    AttendanceModel,
    ChildGuardianModel,
    ChildModel,
    FamilyModel,
    GuardianModel,
    RoomModel,
    ServiceModel,
    SessionModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    ChildGuardianRepository,
    ChildRepository,
    FamilyRepository,
    GuardianRepository,
    SqlAlchemyAddChildGuardianRepository,
    SqlAlchemyCheckInRepository,
    SqlAlchemyCheckOutRepository,
    SqlAlchemyChildAttendanceHistoryRepository,
    SqlAlchemyCreateRoomRepository,
    SqlAlchemyCreateServiceRepository,
    SqlAlchemyGetChildDetailsRepository,
    SqlAlchemyGetFamilyDetailsRepository,
    SqlAlchemyGetGuardianDetailsRepository,
    SqlAlchemyListChildrenRepository,
    SqlAlchemyListFamiliesRepository,
    SqlAlchemyListGuardiansRepository,
    SqlAlchemyListRoomsRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemyRemoveChildGuardianRepository,
    SqlAlchemyServiceAttendanceRepository,
    SqlAlchemyUpdateChildGuardianRepository,
    SqlAlchemyUpdateChildRepository,
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

    guardian = Guardian(
        family_id=family_id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child_id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    with Session(engine) as session:
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)

        result = check_out_child(
            CheckOutRequest(
                attendance_id=attendance_id,
                occurred_at=checked_out_at,
                guardian_id=guardian.id,
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
        assert attendance.checked_out_by_guardian_id == guardian.id

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)
        loaded_attendance = repository.get_attendance(attendance_id)

        assert loaded_attendance is not None
        assert loaded_attendance.checked_out_at == checked_out_at
        assert loaded_attendance.checked_out_by_guardian_id == guardian.id


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

    guardian = Guardian(
        family_id=family_id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child_id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    with Session(engine) as session:
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)

        check_out_child(
            CheckOutRequest(
                attendance_id=attendance_id,
                occurred_at=datetime(2026, 10, 4, 20, 0),
                guardian_id=guardian.id,
            ),
            repository,
        )

        session.rollback()

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, attendance_id)

        assert attendance is not None
        assert attendance.checked_in_at == checked_in_at
        assert attendance.checked_out_at is None
        assert attendance.checked_out_by_guardian_id is None


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


def test_create_room_persists_room(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = SqlAlchemyCreateRoomRepository(session)

        result = create_room(
            CreateRoomRequest(name="Kids 3-5"),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        room = session.get(RoomModel, result.room_id)

        assert room is not None
        assert room.name == "Kids 3-5"
        assert room.is_active is True


def test_list_rooms_returns_only_active_rooms(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                RoomModel(
                    id=uuid4(),
                    name="Sala Kids",
                    is_active=True,
                ),
                RoomModel(
                    id=uuid4(),
                    name="Sala Infantil",
                    is_active=True,
                ),
                RoomModel(
                    id=uuid4(),
                    name="Sala Antiga",
                    is_active=False,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyListRoomsRepository(session)

        result = list_rooms(repository)

    assert len(result) == 2
    assert [room.name for room in result] == [
        "Sala Infantil",
        "Sala Kids",
    ]


def test_create_room_repository_finds_equivalent_name(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            RoomModel(
                id=uuid4(),
                name="Sala Infantil",
                is_active=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCreateRoomRepository(session)

        assert repository.room_name_exists("Sala Infantil") is True
        assert repository.room_name_exists("sala infantil") is True
        assert repository.room_name_exists("  SALA   INFANTIL  ") is True
        assert repository.room_name_exists("Sala Juvenil") is False

    engine.dispose()


def test_create_room_repository_persists_normalized_name(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "normalized_room_test.db")
    Base.metadata.create_all(engine)

    room = Room(name="  SALA   INFANTIL  ")

    with Session(engine) as session:
        repository = SqlAlchemyCreateRoomRepository(session)
        repository.add_room(room)
        session.commit()

    with Session(engine) as session:
        normalized_name = session.execute(
            text(
                """
                SELECT normalized_name
                FROM rooms
                WHERE id = :room_id
                """
            ),
            {"room_id": room.id.hex},
        ).scalar_one()

    assert normalized_name == "sala infantil"

    engine.dispose()


def test_list_children_searches_active_children_by_partial_name(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2020, 5, 12),
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="Mariana Costa",
                    birth_date=date(2019, 3, 10),
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="Maria Oliveira",
                    birth_date=date(2021, 7, 15),
                    is_active=False,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="João Santos",
                    birth_date=date(2020, 1, 20),
                    is_active=True,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyListChildrenRepository(session)

        result = list_children(repository, name="MARIA")

    assert [child.full_name for child in result] == [
        "Maria Silva",
        "Mariana Costa",
    ]
    assert all(child.family_id == family_id for child in result)

    engine.dispose()


def test_get_child_details_returns_only_linked_guardians(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    other_child_id = uuid4()
    guardian_id = uuid4()
    other_guardian_id = uuid4()

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=child_id,
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                ChildModel(
                    id=other_child_id,
                    family_id=family_id,
                    full_name="João Silva",
                    birth_date=date(2020, 3, 15),
                    is_active=True,
                ),
                GuardianModel(
                    id=guardian_id,
                    family_id=family_id,
                    full_name="Ana Silva",
                    phone="82999999999",
                    is_active=True,
                ),
                GuardianModel(
                    id=other_guardian_id,
                    family_id=family_id,
                    full_name="Carlos Silva",
                    phone=None,
                    is_active=False,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=child_id,
                    guardian_id=guardian_id,
                    relationship="Mother",
                    authorized_pickup=True,
                ),
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=other_child_id,
                    guardian_id=other_guardian_id,
                    relationship="Father",
                    authorized_pickup=False,
                ),
            ]
        )
        session.commit()

        repository = SqlAlchemyGetChildDetailsRepository(session)
        result = get_child_details(repository, child_id=child_id)

        assert result is not None
        assert result.id == child_id
        assert result.full_name == "Maria Silva"
        assert len(result.guardians) == 1

        guardian = result.guardians[0]

        assert guardian.id == guardian_id
        assert guardian.full_name == "Ana Silva"
        assert guardian.phone == "82999999999"
        assert guardian.relationship == "Mother"
        assert guardian.authorized_pickup is True
        assert guardian.is_active is True

    engine.dispose()


def test_check_out_child_allows_authorized_guardian_from_another_family(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    another_family_id = uuid4()
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
            FamilyModel(
                id=another_family_id,
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

    guardian = Guardian(
        family_id=another_family_id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child_id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    with Session(engine) as session:
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)

        result = check_out_child(
            CheckOutRequest(
                attendance_id=attendance_id,
                occurred_at=checked_out_at,
                guardian_id=guardian.id,
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
        assert attendance.checked_out_by_guardian_id == guardian.id

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)
        loaded_attendance = repository.get_attendance(attendance_id)

        assert loaded_attendance is not None
        assert loaded_attendance.checked_out_at == checked_out_at
        assert loaded_attendance.checked_out_by_guardian_id == guardian.id


def test_check_out_child_rejects_unauthorized_guardian_from_another_family(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    another_family_id = uuid4()
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
            FamilyModel(
                id=another_family_id,
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

    guardian = Guardian(
        family_id=another_family_id,
        full_name="Maria Silva",
    )
    link = ChildGuardian(
        child_id=child_id,
        guardian_id=guardian.id,
        authorized_pickup=False,
    )

    with Session(engine) as session:
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)

        with pytest.raises(GuardianNotAuthorizedForPickupError):
            check_out_child(
                CheckOutRequest(
                    attendance_id=attendance_id,
                    occurred_at=checked_out_at,
                    guardian_id=guardian.id,
                ),
                repository,
            )

    with Session(engine) as session:
        attendance = session.get(AttendanceModel, attendance_id)

        assert attendance is not None
        assert attendance.checked_out_at is None
        assert attendance.checked_out_by_guardian_id is None

    with Session(engine) as session:
        repository = SqlAlchemyCheckOutRepository(session)
        loaded_attendance = repository.get_attendance(attendance_id)

        assert loaded_attendance is not None
        assert loaded_attendance.checked_out_at is None
        assert loaded_attendance.checked_out_by_guardian_id is None


def test_add_child_guardian_persists_cross_family_link(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    child_family = Family()
    guardian_family = Family()

    child = Child(
        family_id=child_family.id,
        full_name="Test Child",
        birth_date=date(2021, 1, 1),
    )

    guardian = Guardian(
        family_id=guardian_family.id,
        full_name="Maria Silva",
    )

    with Session(engine) as session:
        FamilyRepository(session).add(child_family)
        FamilyRepository(session).add(guardian_family)
        session.flush()

        ChildRepository(session).add(child)
        GuardianRepository(session).add(guardian)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyAddChildGuardianRepository(session)

        result = add_child_guardian(
            AddChildGuardianRequest(
                child_id=child.id,
                guardian_id=guardian.id,
                relationship="Grandmother",
                authorized_pickup=True,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        link = session.get(ChildGuardianModel, result.link_id)

        assert link is not None
        assert link.child_id == child.id
        assert link.guardian_id == guardian.id
        assert link.relationship == "Grandmother"
        assert link.authorized_pickup is True

        assert len(session.scalars(select(FamilyModel)).all()) == 2
        assert len(session.scalars(select(ChildModel)).all()) == 1
        assert len(session.scalars(select(GuardianModel)).all()) == 1
        assert len(session.scalars(select(ChildGuardianModel)).all()) == 1

    engine.dispose()


def test_add_child_guardian_rejects_existing_database_link(
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
        full_name="Maria Silva",
    )
    existing_link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(child)
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(existing_link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyAddChildGuardianRepository(session)

        with pytest.raises(DuplicateChildGuardianError):
            add_child_guardian(
                AddChildGuardianRequest(
                    child_id=child.id,
                    guardian_id=guardian.id,
                    relationship="Mother",
                    authorized_pickup=True,
                ),
                repository,
            )

    with Session(engine) as session:
        links = session.scalars(select(ChildGuardianModel)).all()

        assert len(links) == 1
        assert links[0].id == existing_link.id
        assert links[0].authorized_pickup is True

    engine.dispose()


def test_add_new_guardian_to_existing_child_persists(
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

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(child)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyAddChildGuardianRepository(session)

        result = add_child_guardian(
            AddChildGuardianRequest(
                child_id=child.id,
                full_name="Ana Silva",
                phone="82999999999",
                relationship="Grandmother",
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        guardians = session.scalars(select(GuardianModel)).all()
        links = session.scalars(select(ChildGuardianModel)).all()

        assert len(guardians) == 1
        guardian = guardians[0]

        assert guardian.family_id == family.id
        assert guardian.full_name == "Ana Silva"
        assert guardian.phone == "82999999999"
        assert guardian.is_active is True

        assert len(links) == 1
        link = links[0]

        assert link.id == result.link_id
        assert link.child_id == child.id
        assert link.guardian_id == guardian.id
        assert link.relationship == "Grandmother"
        assert link.authorized_pickup is False

        assert len(session.scalars(select(FamilyModel)).all()) == 1
        assert len(session.scalars(select(ChildModel)).all()) == 1

    engine.dispose()


def test_update_child_guardian_persists_changes(
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
        full_name="Existing Guardian",
    )
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        relationship="Uncle",
        authorized_pickup=False,
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(child)
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateChildGuardianRepository(session)

        update_child_guardian(
            UpdateChildGuardianRequest(
                child_id=child.id,
                guardian_id=guardian.id,
                relationship="Grandfather",
                authorized_pickup=True,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        persisted_link = session.get(ChildGuardianModel, link.id)

        assert persisted_link is not None
        assert persisted_link.child_id == child.id
        assert persisted_link.guardian_id == guardian.id
        assert persisted_link.relationship == "Grandfather"
        assert persisted_link.authorized_pickup is True

    engine.dispose()


def test_update_child_guardian_does_not_affect_other_children(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()

    first_child = Child(
        family_id=family.id,
        full_name="First Child",
        birth_date=date(2021, 1, 1),
    )
    second_child = Child(
        family_id=family.id,
        full_name="Second Child",
        birth_date=date(2022, 1, 1),
    )
    guardian = Guardian(
        family_id=family.id,
        full_name="Shared Guardian",
    )

    first_link = ChildGuardian(
        child_id=first_child.id,
        guardian_id=guardian.id,
        relationship="Uncle",
        authorized_pickup=False,
    )
    second_link = ChildGuardian(
        child_id=second_child.id,
        guardian_id=guardian.id,
        relationship="Uncle",
        authorized_pickup=False,
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(first_child)
        ChildRepository(session).add(second_child)
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(first_link)
        ChildGuardianRepository(session).add(second_link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyUpdateChildGuardianRepository(session)

        update_child_guardian(
            UpdateChildGuardianRequest(
                child_id=first_child.id,
                guardian_id=guardian.id,
                authorized_pickup=True,
            ),
            repository,
        )
        session.commit()

    with Session(engine) as session:
        persisted_first = session.get(
            ChildGuardianModel,
            first_link.id,
        )
        persisted_second = session.get(
            ChildGuardianModel,
            second_link.id,
        )

        assert persisted_first is not None
        assert persisted_second is not None

        assert persisted_first.authorized_pickup is True
        assert persisted_second.authorized_pickup is False

        assert persisted_first.relationship == "Uncle"
        assert persisted_second.relationship == "Uncle"

    engine.dispose()


def test_remove_child_guardian_persists_deletion(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()

    first_child = Child(
        family_id=family.id,
        full_name="First Child",
        birth_date=date(2021, 1, 1),
    )
    second_child = Child(
        family_id=family.id,
        full_name="Second Child",
        birth_date=date(2022, 1, 1),
    )
    guardian = Guardian(
        family_id=family.id,
        full_name="Shared Guardian",
    )

    first_link = ChildGuardian(
        child_id=first_child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )
    second_link = ChildGuardian(
        child_id=second_child.id,
        guardian_id=guardian.id,
        authorized_pickup=True,
    )

    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(first_child)
        ChildRepository(session).add(second_child)
        GuardianRepository(session).add(guardian)
        session.flush()

        ChildGuardianRepository(session).add(first_link)
        ChildGuardianRepository(session).add(second_link)
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyRemoveChildGuardianRepository(session)

        remove_child_guardian(
            RemoveChildGuardianRequest(
                child_id=first_child.id,
                guardian_id=guardian.id,
            ),
            repository,
        )

        session.commit()

    with Session(engine) as session:
        assert session.get(ChildGuardianModel, first_link.id) is None

        remaining_link = session.get(
            ChildGuardianModel,
            second_link.id,
        )
        assert remaining_link is not None
        assert remaining_link.authorized_pickup is True

        assert session.get(ChildModel, first_child.id) is not None
        assert session.get(ChildModel, second_child.id) is not None
        assert session.get(GuardianModel, guardian.id) is not None

    engine.dispose()


def test_child_attendance_history_loads_related_data(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()

    service_starts_at = datetime(2026, 10, 25, 9, 0)
    checked_in_at = datetime(2026, 10, 25, 9, 10)
    checked_out_at = datetime(2026, 10, 25, 11, 0)

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=child_id,
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                GuardianModel(
                    id=guardian_id,
                    family_id=family_id,
                    full_name="João Silva",
                    is_active=True,
                ),
                ServiceModel(
                    id=service_id,
                    name="Sunday Morning",
                    starts_at=service_starts_at,
                    ends_at=None,
                ),
                RoomModel(
                    id=room_id,
                    name="Kids 4-6",
                    is_active=True,
                ),
            ]
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 4-6",
                min_age_years=4,
                max_age_years=6,
                status="CLOSED",
            )
        )
        session.flush()

        session.add(
            AttendanceModel(
                id=attendance_id,
                child_id=child_id,
                session_id=session_id,
                checked_in_at=checked_in_at,
                checked_out_at=checked_out_at,
                checked_out_by_guardian_id=guardian_id,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyChildAttendanceHistoryRepository(session)

        result = repository.list_by_child(child_id)

        assert len(result) == 1

        item = result[0]

        assert item.attendance_id == attendance_id
        assert item.child_id == child_id
        assert item.service_name == "Sunday Morning"
        assert item.service_starts_at == service_starts_at
        assert item.room_name == "Kids 4-6"
        assert item.checked_in_at == checked_in_at
        assert item.checked_out_at == checked_out_at
        assert item.checked_out_by_guardian_name == "João Silva"

    engine.dispose()


def test_child_attendance_history_includes_open_attendance(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    child_id = uuid4()
    other_child_id = uuid4()
    service_id = uuid4()
    room_id = uuid4()
    session_id = uuid4()
    attendance_id = uuid4()
    older_attendance_id = uuid4()

    checked_in_at = datetime(2026, 10, 25, 9, 10)

    with Session(engine) as session:
        session.add(
            FamilyModel(id=family_id, is_active=True)
        )
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=child_id,
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                ChildModel(
                    id=other_child_id,
                    family_id=family_id,
                    full_name="Pedro Silva",
                    birth_date=date(2020, 3, 15),
                    is_active=True,
                ),
                ServiceModel(
                    id=service_id,
                    name="Sunday Morning",
                    starts_at=datetime(2026, 10, 25, 9, 0),
                    ends_at=None,
                ),
                RoomModel(
                    id=room_id,
                    name="Kids 4-6",
                    is_active=True,
                ),
            ]
        )
        session.flush()

        session.add(
            SessionModel(
                id=session_id,
                service_id=service_id,
                room_id=room_id,
                name="Kids 4-6",
                min_age_years=4,
                max_age_years=6,
                status="OPEN",
            )
        )
        session.flush()

        session.add_all(
            [
                AttendanceModel(
                    id=attendance_id,
                    child_id=child_id,
                    session_id=session_id,
                    checked_in_at=checked_in_at,
                    checked_out_at=None,
                    checked_out_by_guardian_id=None,
                ),
                AttendanceModel(
                    id=older_attendance_id,
                    child_id=child_id,
                    session_id=session_id,
                    checked_in_at=datetime(2026, 10, 18, 9, 5),
                    checked_out_at=datetime(2026, 10, 18, 11, 0),
                    checked_out_by_guardian_id=None,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyChildAttendanceHistoryRepository(session)

        result = repository.list_by_child(child_id)

        assert len(result) == 2

        assert [item.attendance_id for item in result] == [
            attendance_id,
            older_attendance_id,
        ]

        assert result[0].child_id == child_id
        assert result[0].checked_in_at == checked_in_at
        assert result[0].checked_out_at is None
        assert result[0].checked_out_by_guardian_name is None

        assert result[1].child_id == child_id
        assert result[1].checked_out_at == datetime(2026, 10, 18, 11, 0)

    engine.dispose()


def test_list_service_attendances_returns_only_active_attendances(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()

    present_child_id = uuid4()
    checked_out_child_id = uuid4()
    other_service_child_id = uuid4()
    nursery_child_id = uuid4()
    nursery_attendance_id = uuid4()

    service_id = uuid4()
    other_service_id = uuid4()

    room_id = uuid4()
    other_room_id = uuid4()
    other_room_session_id = uuid4()
    session_id = uuid4()
    other_session_id = uuid4()

    present_attendance_id = uuid4()
    checked_in_at = datetime(2026, 10, 25, 9, 10)

    with Session(engine) as session:
        session.add(
            FamilyModel(
                id=family_id,
                is_active=True,
            )
        )
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=present_child_id,
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                ChildModel(
                    id=checked_out_child_id,
                    family_id=family_id,
                    full_name="Pedro Silva",
                    birth_date=date(2020, 3, 15),
                    is_active=True,
                ),
                ChildModel(
                    id=other_service_child_id,
                    family_id=family_id,
                    full_name="Ana Silva",
                    birth_date=date(2021, 8, 20),
                    is_active=True,
                ),
                ChildModel(
                    id=nursery_child_id,
                    family_id=family_id,
                    full_name="Beatriz Silva",
                    birth_date=date(2024, 3, 15),
                    is_active=True,
                ),
                ServiceModel(
                    id=service_id,
                    name="Sunday Morning",
                    starts_at=datetime(2026, 10, 25, 9, 0),
                    ends_at=None,
                ),
                ServiceModel(
                    id=other_service_id,
                    name="Sunday Evening",
                    starts_at=datetime(2026, 10, 25, 18, 0),
                    ends_at=None,
                ),
                RoomModel(
                    id=room_id,
                    name="Kids 4-6",
                    is_active=True,
                ),
                RoomModel(
                    id=other_room_id,
                    name="Nursery",
                    is_active=True,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                SessionModel(
                    id=session_id,
                    service_id=service_id,
                    room_id=room_id,
                    name="Kids 4-6 Morning",
                    min_age_years=4,
                    max_age_years=6,
                    status="OPEN",
                ),
                SessionModel(
                    id=other_session_id,
                    service_id=other_service_id,
                    room_id=room_id,
                    name="Kids 4-6 Evening",
                    min_age_years=4,
                    max_age_years=6,
                    status="OPEN",
                ),
                SessionModel(
                    id=other_room_session_id,
                    service_id=service_id,
                    room_id=other_room_id,
                    name="Nursery Morning",
                    min_age_years=0,
                    max_age_years=3,
                    status="OPEN",
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                AttendanceModel(
                    id=present_attendance_id,
                    child_id=present_child_id,
                    session_id=session_id,
                    checked_in_at=checked_in_at,
                    checked_out_at=None,
                    checked_out_by_guardian_id=None,
                ),
                AttendanceModel(
                    id=uuid4(),
                    child_id=checked_out_child_id,
                    session_id=session_id,
                    checked_in_at=datetime(2026, 10, 25, 9, 5),
                    checked_out_at=datetime(2026, 10, 25, 11, 0),
                    checked_out_by_guardian_id=None,
                ),
                AttendanceModel(
                    id=uuid4(),
                    child_id=other_service_child_id,
                    session_id=other_session_id,
                    checked_in_at=datetime(2026, 10, 25, 18, 10),
                    checked_out_at=None,
                    checked_out_by_guardian_id=None,
                ),
                AttendanceModel(
                    id=nursery_attendance_id,
                    child_id=nursery_child_id,
                    session_id=other_room_session_id,
                    checked_in_at=datetime(2026, 10, 25, 9, 20),
                    checked_out_at=None,
                    checked_out_by_guardian_id=None,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyServiceAttendanceRepository(session)

        result = repository.list_active_by_service(service_id)

        assert len(result) == 2

        assert [
            (item.room_name, item.child_name)
            for item in result
        ] == [
            ("Kids 4-6", "Maria Silva"),
            ("Nursery", "Beatriz Silva"),
        ]

        assert {item.attendance_id for item in result} == {
            present_attendance_id,
            nursery_attendance_id,
        }

        assert all(item.checked_out_at is None for item in result)
        assert all(item.service_id == service_id for item in result)

    engine.dispose()


def test_search_active_families_matches_children_and_guardians(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_by_child_id = uuid4()
    family_by_guardian_id = uuid4()
    inactive_family_id = uuid4()
    unrelated_family_id = uuid4()

    with Session(engine) as session:
        session.add_all(
            [
                FamilyModel(id=family_by_child_id, is_active=True),
                FamilyModel(id=family_by_guardian_id, is_active=True),
                FamilyModel(id=inactive_family_id, is_active=False),
                FamilyModel(id=unrelated_family_id, is_active=True),
            ]
        )
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=uuid4(),
                    family_id=family_by_child_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                GuardianModel(
                    id=uuid4(),
                    family_id=family_by_child_id,
                    full_name="Maria Oliveira",
                    is_active=True,
                ),
                GuardianModel(
                    id=uuid4(),
                    family_id=family_by_guardian_id,
                    full_name="Maria Santos",
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=inactive_family_id,
                    full_name="Maria Costa",
                    birth_date=date(2020, 3, 15),
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=unrelated_family_id,
                    full_name="Pedro Souza",
                    birth_date=date(2021, 8, 20),
                    is_active=True,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyListFamiliesRepository(session)

        result = repository.search_active_families("mArIa")

        assert {family.id for family in result} == {
            family_by_child_id,
            family_by_guardian_id,
        }
        assert len(result) == 2
        assert all(family.is_active for family in result)

    engine.dispose()


def test_get_family_details_repository_loads_family_members(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    other_family_id = uuid4()
    child_id = uuid4()
    guardian_id = uuid4()

    with Session(engine) as session:
        session.add_all(
            [
                FamilyModel(id=family_id, is_active=True),
                FamilyModel(id=other_family_id, is_active=True),
            ]
        )
        session.flush()

        session.add_all(
            [
                ChildModel(
                    id=child_id,
                    family_id=family_id,
                    full_name="Maria Silva",
                    birth_date=date(2021, 5, 10),
                    is_active=True,
                ),
                GuardianModel(
                    id=guardian_id,
                    family_id=family_id,
                    full_name="João Silva",
                    phone="82999999999",
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=other_family_id,
                    full_name="Pedro Souza",
                    birth_date=date(2020, 3, 15),
                    is_active=True,
                ),
                GuardianModel(
                    id=uuid4(),
                    family_id=other_family_id,
                    full_name="Ana Souza",
                    is_active=True,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyGetFamilyDetailsRepository(session)

        family = repository.get_family(family_id)
        children = repository.get_children_for_family(family_id)
        guardians = repository.get_guardians_for_family(family_id)

        assert family is not None
        assert family.id == family_id
        assert family.is_active is True

        assert len(children) == 1
        assert children[0].id == child_id
        assert children[0].full_name == "Maria Silva"

        assert len(guardians) == 1
        assert guardians[0].id == guardian_id
        assert guardians[0].full_name == "João Silva"
        assert guardians[0].phone == "82999999999"

    engine.dispose()


def test_search_active_guardians_matches_name_case_insensitively(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family_id = uuid4()
    maria_id = uuid4()
    mariana_id = uuid4()

    with Session(engine) as session:
        session.add(FamilyModel(id=family_id, is_active=True))
        session.flush()

        session.add_all(
            [
                GuardianModel(
                    id=maria_id,
                    family_id=family_id,
                    full_name="Maria Oliveira",
                    phone="82999999999",
                    is_active=True,
                ),
                GuardianModel(
                    id=mariana_id,
                    family_id=family_id,
                    full_name="Mariana Silva",
                    is_active=True,
                ),
                GuardianModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="Maria Souza",
                    is_active=False,
                ),
                GuardianModel(
                    id=uuid4(),
                    family_id=family_id,
                    full_name="João Santos",
                    is_active=True,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyListGuardiansRepository(session)

        results = repository.search_active_guardians("mArIa")

        assert [guardian.id for guardian in results] == [
            maria_id,
            mariana_id,
        ]
        assert all(guardian.is_active for guardian in results)
        assert results[0].phone == "82999999999"

    engine.dispose()


def test_get_guardian_details_repository_loads_children_across_families(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    guardian_family_id = uuid4()
    other_family_id = uuid4()
    guardian_id = uuid4()
    first_child_id = uuid4()
    second_child_id = uuid4()

    with Session(engine) as session:
        session.add_all(
            [
                FamilyModel(id=guardian_family_id, is_active=True),
                FamilyModel(id=other_family_id, is_active=True),
            ]
        )
        session.flush()

        session.add_all(
            [
                GuardianModel(
                    id=guardian_id,
                    family_id=guardian_family_id,
                    full_name="Maria Oliveira",
                    phone="82999999999",
                    is_active=True,
                ),
                ChildModel(
                    id=first_child_id,
                    family_id=guardian_family_id,
                    full_name="Ana Oliveira",
                    birth_date=date(2020, 5, 10),
                    is_active=True,
                ),
                ChildModel(
                    id=second_child_id,
                    family_id=other_family_id,
                    full_name="Pedro Silva",
                    birth_date=date(2021, 8, 15),
                    is_active=True,
                ),
                ChildModel(
                    id=uuid4(),
                    family_id=other_family_id,
                    full_name="Unlinked Child",
                    birth_date=date(2022, 1, 1),
                    is_active=True,
                ),
            ]
        )
        session.flush()

        session.add_all(
            [
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=first_child_id,
                    guardian_id=guardian_id,
                    relationship="Mother",
                    authorized_pickup=True,
                ),
                ChildGuardianModel(
                    id=uuid4(),
                    child_id=second_child_id,
                    guardian_id=guardian_id,
                    relationship="Aunt",
                    authorized_pickup=False,
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyGetGuardianDetailsRepository(session)

        guardian = repository.get_guardian(guardian_id)
        children = repository.get_children_for_guardian(guardian_id)

        assert guardian is not None
        assert guardian.id == guardian_id
        assert guardian.family_id == guardian_family_id

        assert len(children) == 2

        first_child, first_link = children[0]
        assert first_child.id == first_child_id
        assert first_child.family_id == guardian_family_id
        assert first_link.relationship == "Mother"
        assert first_link.authorized_pickup is True

        second_child, second_link = children[1]
        assert second_child.id == second_child_id
        assert second_child.family_id == other_family_id
        assert second_link.relationship == "Aunt"
        assert second_link.authorized_pickup is False

    engine.dispose()


def test_update_child_repository_persists_changes(
    tmp_path: Path,
) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    Base.metadata.create_all(engine)

    family = Family()
    child = Child(
        family_id=family.id,
        full_name="Maria Silva",
        birth_date=date(2021, 5, 10),
    )

    # Create the original records.
    with Session(engine) as session:
        FamilyRepository(session).add(family)
        session.flush()

        ChildRepository(session).add(child)
        session.commit()

    # Update through the application use case.
    with Session(engine) as session:
        repository = SqlAlchemyUpdateChildRepository(session)

        update_child(
            UpdateChildRequest(
                child_id=child.id,
                full_name="Maria Oliveira",
            ),
            repository,
        )

        session.commit()

    # Verify persistence using a new database session.
    with Session(engine) as session:
        saved_child = ChildRepository(session).get(child.id)

        assert saved_child is not None
        assert saved_child.full_name == "Maria Oliveira"
        assert saved_child.birth_date == date(2021, 5, 10)
        assert saved_child.family_id == family.id
        assert saved_child.is_active is True
