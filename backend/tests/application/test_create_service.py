from datetime import datetime

from church_city_kids.application.create_service import (
    CreateServiceRequest,
    create_service,
)
from church_city_kids.domain.scheduling import Service


class FakeCreateServiceRepository:
    def __init__(self) -> None:
        self.added_services: list[Service] = []

    def add_service(self, service: Service) -> None:
        self.added_services.append(service)


def test_create_service_creates_service() -> None:
    repository = FakeCreateServiceRepository()

    request = CreateServiceRequest(
        name="Sunday Service",
        starts_at=datetime(2026, 10, 4, 19, 0),
        ends_at=datetime(2026, 10, 4, 21, 0),
    )

    result = create_service(request, repository)

    assert len(repository.added_services) == 1

    service = repository.added_services[0]

    assert service.id == result.service_id
    assert service.name == "Sunday Service"
    assert service.starts_at == datetime(2026, 10, 4, 19, 0)
    assert service.ends_at == datetime(2026, 10, 4, 21, 0)
