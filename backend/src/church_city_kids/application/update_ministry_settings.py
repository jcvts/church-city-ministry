from dataclasses import dataclass
from typing import Protocol

from church_city_kids.domain.settings import MinistrySettings


@dataclass(frozen=True)
class UpdateMinistrySettingsRequest:
    pager_required: bool


class MinistrySettingsRepository(Protocol):
    def get(self) -> MinistrySettings | None: ...

    def save(self, settings: MinistrySettings) -> None: ...


def update_ministry_settings(
    request: UpdateMinistrySettingsRequest,
    repository: MinistrySettingsRepository,
) -> None:
    settings = repository.get()

    if settings is None:
        raise ValueError("Ministry settings not found")

    settings.pager_required = request.pager_required

    repository.save(settings)
