import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.infrastructure.persistence.base import Base
from church_city_kids.infrastructure.persistence.models import (
    MinistrySettingsModel,
)


def test_ministry_settings_are_persisted(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    engine = create_engine(database_url)

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
        settings = session.scalar(
            select(MinistrySettingsModel).where(
                MinistrySettingsModel.id == 1
            )
        )

        assert settings is not None
        assert settings.pager_required is False

    engine.dispose()


def test_ministry_settings_reject_invalid_id(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'invalid_settings.db'}"
    engine = create_engine(database_url)

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            MinistrySettingsModel(
                id=2,
                pager_required=False,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

    engine.dispose()
