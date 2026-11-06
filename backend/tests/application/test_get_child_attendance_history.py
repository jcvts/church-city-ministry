from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.application.get_child_attendance_history import (
    ChildAttendanceHistoryItem,
    get_child_attendance_history,
)


class FakeAttendanceHistoryRepository:
    def __init__(
        self,
        items: list[ChildAttendanceHistoryItem],
    ) -> None:
        self.items = items

    def list_by_child(
        self,
        child_id: UUID,
    ) -> list[ChildAttendanceHistoryItem]:
        return [item for item in self.items if item.child_id == child_id]


def test_get_child_attendance_history_returns_newest_first() -> None:
    child_id = uuid4()

    older = ChildAttendanceHistoryItem(
        attendance_id=uuid4(),
        child_id=child_id,
        service_name="Sunday Morning",
        service_starts_at=datetime(2026, 10, 18, 9, 0),
        room_name="Kids 4-6",
        checked_in_at=datetime(2026, 10, 18, 9, 5),
        checked_out_at=datetime(2026, 10, 18, 11, 0),
        checked_out_by_guardian_name="Maria Silva",
    )

    newer = ChildAttendanceHistoryItem(
        attendance_id=uuid4(),
        child_id=child_id,
        service_name="Sunday Morning",
        service_starts_at=datetime(2026, 10, 25, 9, 0),
        room_name="Kids 4-6",
        checked_in_at=datetime(2026, 10, 25, 9, 10),
        checked_out_at=None,
        checked_out_by_guardian_name=None,
    )

    repository = FakeAttendanceHistoryRepository([older, newer])

    result = get_child_attendance_history(child_id, repository)

    assert result == [newer, older]
    assert result[0].checked_out_at is None
    assert result[0].checked_out_by_guardian_name is None


def test_get_child_attendance_history_returns_empty_list() -> None:
    child_id = uuid4()

    repository = FakeAttendanceHistoryRepository([])

    result = get_child_attendance_history(
        child_id,
        repository,
    )

    assert result == []
