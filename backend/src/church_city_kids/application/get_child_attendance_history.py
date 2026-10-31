from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ChildAttendanceHistoryItem:
    attendance_id: UUID
    child_id: UUID
    service_name: str
    service_starts_at: datetime
    room_name: str
    checked_in_at: datetime
    checked_out_at: datetime | None
    checked_out_by_guardian_name: str | None


class ChildAttendanceHistoryRepository(Protocol):
    def list_by_child(
        self,
        child_id: UUID,
    ) -> list[ChildAttendanceHistoryItem]: ...


def get_child_attendance_history(
    child_id: UUID,
    repository: ChildAttendanceHistoryRepository,
) -> list[ChildAttendanceHistoryItem]:
    items = repository.list_by_child(child_id)

    return sorted(
        items,
        key=lambda item: (item.checked_in_at, item.attendance_id),
        reverse=True,
    )
