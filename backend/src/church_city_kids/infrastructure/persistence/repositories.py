from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from church_city_kids.application.check_in import CheckInRepository
from church_city_kids.application.check_out import CheckOutRepository
from church_city_kids.application.create_service import CreateServiceRepository
from church_city_kids.application.registration import RegistrationRepository
from church_city_kids.domain.attendance import Attendance
from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)
from church_city_kids.domain.scheduling import Service, SessionStatus
from church_city_kids.domain.scheduling import Session as KidsSession
from church_city_kids.infrastructure.persistence.models import (
    AttendanceModel,
    ChildGuardianModel,
    ChildModel,
    FamilyModel,
    GuardianModel,
    ServiceModel,
    SessionModel,
)


class ChildRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, child: Child) -> None:
        model = ChildModel(
            id=child.id,
            family_id=child.family_id,
            full_name=child.full_name,
            birth_date=child.birth_date,
            is_active=child.is_active,
        )
        self._session.add(model)

    def get(self, child_id: UUID) -> Child | None:
        model = self._session.get(ChildModel, child_id)

        if model is None:
            return None

        return Child(
            id=model.id,
            family_id=model.family_id,
            full_name=model.full_name,
            birth_date=model.birth_date,
            is_active=model.is_active,
        )


class FamilyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, family: Family) -> None:
        self._session.add(
            FamilyModel(
                id=family.id,
                is_active=family.is_active,
            )
        )

    def get(self, family_id: UUID) -> Family | None:
        model = self._session.get(FamilyModel, family_id)

        if model is None:
            return None

        return Family(
            id=model.id,
            is_active=model.is_active,
        )




class GuardianRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, guardian: Guardian) -> None:
        self._session.add(
            GuardianModel(
                id=guardian.id,
                family_id=guardian.family_id,
                full_name=guardian.full_name,
                phone=guardian.phone,
                is_active=guardian.is_active,
            )
        )

    def get(self, guardian_id: UUID) -> Guardian | None:
        model = self._session.get(GuardianModel, guardian_id)

        if model is None:
            return None

        return Guardian(
            id=model.id,
            family_id=model.family_id,
            full_name=model.full_name,
            phone=model.phone,
            is_active=model.is_active,
        )


class ChildGuardianRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, link: ChildGuardian) -> None:
        self._session.add(
            ChildGuardianModel(
                id=link.id,
                child_id=link.child_id,
                guardian_id=link.guardian_id,
                relationship=link.relationship,
                authorized_pickup=link.authorized_pickup,
            )
        )

    def get(self, link_id: UUID) -> ChildGuardian | None:
        model = self._session.get(ChildGuardianModel, link_id)

        if model is None:
            return None

        return ChildGuardian(
            id=model.id,
            child_id=model.child_id,
            guardian_id=model.guardian_id,
            relationship=model.relationship,
            authorized_pickup=model.authorized_pickup,
        )


class SqlAlchemyRegistrationRepository(RegistrationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_family(self, family: Family) -> None:
        FamilyRepository(self._session).add(family)
        self._session.flush()

    def add_guardian(self, guardian: Guardian) -> None:
        GuardianRepository(self._session).add(guardian)

    def add_child(self, child: Child) -> None:
        ChildRepository(self._session).add(child)
        self._session.flush()

    def add_child_guardian(self, link: ChildGuardian) -> None:
        ChildGuardianRepository(self._session).add(link)


class SqlAlchemyCheckInRepository(CheckInRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_child(self, child_id: UUID) -> Child | None:
        return ChildRepository(self._session).get(child_id)

    def get_family(self, family_id: UUID) -> Family | None:
        return FamilyRepository(self._session).get(family_id)

    def get_session(self, session_id: UUID) -> KidsSession | None:
        model = self._session.get(SessionModel, session_id)

        if model is None:
            return None

        return KidsSession(
            id=model.id,
            service_id=model.service_id,
            room_id=model.room_id,
            name=model.name,
            min_age_years=model.min_age_years,
            max_age_years=model.max_age_years,
            status=SessionStatus(model.status.lower()),
        )

    def get_service(self, service_id: UUID) -> Service | None:
        model = self._session.get(ServiceModel, service_id)

        if model is None:
            return None

        return Service(
            id=model.id,
            name=model.name,
            starts_at=model.starts_at,
            ends_at=model.ends_at,
        )

    def get_active_attendances(
        self,
        child_id: UUID,
    ) -> list[Attendance]:
        statement = select(AttendanceModel).where(
            AttendanceModel.child_id == child_id,
            AttendanceModel.checked_out_at.is_(None),
        )

        models = self._session.scalars(statement).all()

        return [
            Attendance(
                id=model.id,
                child_id=model.child_id,
                session_id=model.session_id,
                checked_in_at=model.checked_in_at,
                checked_out_at=model.checked_out_at,
            )
            for model in models
        ]

    def add_attendance(self, attendance: Attendance) -> None:
        self._session.add(
            AttendanceModel(
                id=attendance.id,
                child_id=attendance.child_id,
                session_id=attendance.session_id,
                checked_in_at=attendance.checked_in_at,
                checked_out_at=attendance.checked_out_at,
            )
        )


class SqlAlchemyCheckOutRepository(CheckOutRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_attendance(
        self,
        attendance_id: UUID,
    ) -> Attendance | None:
        model = self._session.get(AttendanceModel, attendance_id)

        if model is None:
            return None

        return Attendance(
            id=model.id,
            child_id=model.child_id,
            session_id=model.session_id,
            checked_in_at=model.checked_in_at,
            checked_out_at=model.checked_out_at,
        )

    def save_attendance(
        self,
        attendance: Attendance,
    ) -> None:
        model = self._session.get(AttendanceModel, attendance.id)

        if model is None:
            return

        model.checked_out_at = attendance.checked_out_at


class SqlAlchemyCreateServiceRepository(CreateServiceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_service(self, service: Service) -> None:
        self._session.add(
            ServiceModel(
                id=service.id,
                name=service.name,
                starts_at=service.starts_at,
                ends_at=service.ends_at,
            )
        )
