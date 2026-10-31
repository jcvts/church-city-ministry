import pytest

from church_city_kids.application.update_ministry_settings import (
    UpdateMinistrySettingsRequest,
    update_ministry_settings,
)
from church_city_kids.domain.settings import MinistrySettings


class FakeMinistrySettingsRepository:
    def __init__(self) -> None:
        self.settings = MinistrySettings()

    def get(self) -> MinistrySettings | None:
        return self.settings

    def save(self, settings: MinistrySettings) -> None:
        self.settings = settings


def test_update_ministry_settings_disables_pager_requirement() -> None:
    repository = FakeMinistrySettingsRepository()

    update_ministry_settings(
        request=UpdateMinistrySettingsRequest(
            pager_required=False,
        ),
        repository=repository,
    )

    assert repository.settings.pager_required is False


def test_update_ministry_settings_fails_when_settings_missing() -> None:
    class MissingSettingsRepository(FakeMinistrySettingsRepository):
        def get(self) -> MinistrySettings | None:
            return None

    repository = MissingSettingsRepository()

    with pytest.raises(
        ValueError,
        match="Ministry settings not found",
    ):
        update_ministry_settings(
            request=UpdateMinistrySettingsRequest(
                pager_required=False,
            ),
            repository=repository,
        )
