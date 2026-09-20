from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from church_city_kids.domain.errors import DuplicateChildGuardianError


def age_in_years(birth_date: date, on_date: date) -> int:
    years = on_date.year - birth_date.year
    if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


@dataclass
class Family:
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class Guardian:
    family_id: UUID
    full_name: str
    id: UUID = field(default_factory=uuid4)
    phone: str | None = None
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class Child:
    family_id: UUID
    full_name: str
    birth_date: date
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False

    def age_on(self, on_date: date) -> int:
        return age_in_years(self.birth_date, on_date)


@dataclass
class ChildGuardian:
    child_id: UUID
    guardian_id: UUID
    id: UUID = field(default_factory=uuid4)
    relationship: str | None = None
    authorized_pickup: bool = True


@dataclass
class Volunteer:
    full_name: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


def link_child_guardian(
    child: Child,
    guardian: Guardian,
    existing: list[ChildGuardian],
    *,
    relationship: str | None = None,
    authorized_pickup: bool = True,
) -> ChildGuardian:
    for link in existing:
        if link.child_id == child.id and link.guardian_id == guardian.id:
            raise DuplicateChildGuardianError()
    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        relationship=relationship,
        authorized_pickup=authorized_pickup,
    )
    existing.append(link)
    return link
