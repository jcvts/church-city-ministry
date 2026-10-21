from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.domain.errors import (
    PagerAlreadyAssignedError,
    PagerInactiveError,
)


@dataclass
class Pager:
    code: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

    def deactivate(self) -> None:
        self.is_active = False


@dataclass
class PagerAssignment:
    pager_id: UUID
    family_id: UUID
    service_id: UUID
    assigned_at: datetime
    id: UUID = field(default_factory=uuid4)
    released_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.released_at is None

    def release(self, occurred_at: datetime) -> None:
        if self.released_at is None:
            self.released_at = occurred_at


def assign_pager(
    *,
    family_id: UUID,
    service_id: UUID,
    pager: Pager,
    active_assignments: list[PagerAssignment],
    occurred_at: datetime,
) -> PagerAssignment:
    if not pager.is_active:
        raise PagerInactiveError()

    for assignment in active_assignments:
        if not assignment.is_active:
            continue

        same_family_and_service = (
            assignment.family_id == family_id
            and assignment.service_id == service_id
        )

        if assignment.pager_id == pager.id:
            if same_family_and_service:
                return assignment

            raise PagerAlreadyAssignedError()

        if same_family_and_service:
            raise PagerAlreadyAssignedError()

    assignment = PagerAssignment(
        pager_id=pager.id,
        family_id=family_id,
        service_id=service_id,
        assigned_at=occurred_at,
    )

    active_assignments.append(assignment)
    return assignment
