from datetime import datetime
from uuid import UUID, uuid4

from church_city_kids.application.list_service_attendances import (
    ServiceAttendanceItem,
    list_service_attendances,
)


class FakeServiceAttendanceRepository:
    def __init__(self, items: list[ServiceAttendanceItem]) -> None:
        self.items = items

    def list_active_by_service(
        self,
        service_id: UUID,
    ) -> list[ServiceAttendanceItem]:
        return [
            item
            for item in self.items
            if item.service_id == service_id
            and item.checked_out_at is None
        ]


def test_list_service_attendances_returns_only_present_children() -> None:
    service_id = uuid4()
    other_service_id = uuid4()

    present_child = ServiceAttendanceItem(
        attendance_id=uuid4(),
        service_id=service_id,
        child_id=uuid4(),
        child_name="Maria Silva",
        room_id=uuid4(),
        room_name="Kids 4-6",
        checked_in_at=datetime(2026, 10, 25, 9, 10),
        checked_out_at=None,
    )

    checked_out_child = ServiceAttendanceItem(
        attendance_id=uuid4(),
        service_id=service_id,
        child_id=uuid4(),
        child_name="Pedro Silva",
        room_id=present_child.room_id,
        room_name="Kids 4-6",
        checked_in_at=datetime(2026, 10, 25, 9, 5),
        checked_out_at=datetime(2026, 10, 25, 11, 0),
    )

    child_from_other_service = ServiceAttendanceItem(
        attendance_id=uuid4(),
        service_id=other_service_id,
        child_id=uuid4(),
        child_name="Ana Silva",
        room_id=uuid4(),
        room_name="Nursery",
        checked_in_at=datetime(2026, 10, 25, 9, 15),
        checked_out_at=None,
    )

    repository = FakeServiceAttendanceRepository(
        [
            present_child,
            checked_out_child,
            child_from_other_service,
        ]
    )

    result = list_service_attendances(service_id, repository)

    assert result == [present_child]
