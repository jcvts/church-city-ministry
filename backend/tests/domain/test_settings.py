from church_city_kids.domain.settings import MinistrySettings


def test_pager_is_required_by_default() -> None:
    settings = MinistrySettings()

    assert settings.pager_required is True


def test_pager_requirement_can_be_disabled() -> None:
    settings = MinistrySettings(pager_required=False)

    assert settings.pager_required is False
