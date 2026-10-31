from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from church_city_kids.application.update_ministry_settings import (
    UpdateMinistrySettingsRequest,
    update_ministry_settings,
)
from church_city_kids.domain.settings import MinistrySettings
from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.models import (
    MinistrySettingsModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyMinistrySettingsRepository,
)


def test_repository_loads_ministry_settings(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'settings_repository.db'}"
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            MinistrySettingsModel(
                id=1,
                pager_required=False,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMinistrySettingsRepository(session)

        settings = repository.get()

        assert settings is not None
        assert settings.pager_required is False

    engine.dispose()


def test_repository_updates_ministry_settings(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'settings_update.db'}"
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            MinistrySettingsModel(
                id=1,
                pager_required=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMinistrySettingsRepository(session)

        repository.save(
            MinistrySettings(pager_required=False)
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMinistrySettingsRepository(session)
        settings = repository.get()

        assert settings is not None
        assert settings.pager_required is False

    engine.dispose()


def test_update_ministry_settings_persists_through_repository(
    tmp_path,
) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'settings_use_case.db'}"
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            MinistrySettingsModel(
                id=1,
                pager_required=True,
            )
        )
        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMinistrySettingsRepository(session)

        update_ministry_settings(
            request=UpdateMinistrySettingsRequest(
                pager_required=False,
            ),
            repository=repository,
        )

        session.commit()

    with Session(engine) as session:
        repository = SqlAlchemyMinistrySettingsRepository(session)
        settings = repository.get()

        assert settings is not None
        assert settings.pager_required is False

    engine.dispose()
