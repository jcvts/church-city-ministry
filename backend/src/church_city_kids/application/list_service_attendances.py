from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ServiceAttendanceItem:
    attendance_id: UUID
    service_id: UUID
    child_id: UUID
    child_name: str
    room_id: UUID
    room_name: str
    checked_in_at: datetime
    checked_out_at: datetime | None


class ServiceAttendanceRepository(Protocol):
    def list_active_by_service(
        self,
        service_id: UUID,
    ) -> list[ServiceAttendanceItem]: ...


def list_service_attendances(
    service_id: UUID,
    repository: ServiceAttendanceRepository,
) -> list[ServiceAttendanceItem]:
    return repository.list_active_by_service(service_id)
