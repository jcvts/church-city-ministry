from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.scheduling import Service


@dataclass(frozen=True)
class CreateServiceRequest:
    name: str
    starts_at: datetime
    ends_at: datetime | None = None


@dataclass(frozen=True)
class CreateServiceResult:
    service_id: UUID


class CreateServiceRepository(Protocol):
    def add_service(self, service: Service) -> None: ...


def create_service(
    request: CreateServiceRequest,
    repository: CreateServiceRepository,
) -> CreateServiceResult:
    service = Service(
        name=request.name,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
    )

    repository.add_service(service)

    return CreateServiceResult(service_id=service.id)
