from uuid import UUID

from sqlalchemy.orm import Session

from church_city_kids.domain.people import (
    Child,
    ChildGuardian,
    Family,
    Guardian,
)
from church_city_kids.infrastructure.persistence.models import (
    ChildGuardianModel,
    ChildModel,
    FamilyModel,
    GuardianModel,
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

