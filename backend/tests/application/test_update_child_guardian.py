from uuid import uuid4

import pytest

from church_city_kids.application.update_child_guardian import (
    ChildGuardianNotFoundError,
    UpdateChildGuardianRequest,
    update_child_guardian,
)
from church_city_kids.domain.people import ChildGuardian


class FakeUpdateChildGuardianRepository:
    def __init__(self, link: ChildGuardian) -> None:
        self.link = link
        self.saved_links: list[ChildGuardian] = []

    def get_child_guardian(
        self,
        child_id,
        guardian_id,
    ) -> ChildGuardian | None:
        if self.link.child_id == child_id and self.link.guardian_id == guardian_id:
            return self.link

        return None

    def save_child_guardian(self, link: ChildGuardian) -> None:
        self.saved_links.append(link)


def test_update_existing_child_guardian_pickup_authorization() -> None:
    link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=uuid4(),
        relationship="Uncle",
        authorized_pickup=False,
    )

    repository = FakeUpdateChildGuardianRepository(link)

    update_child_guardian(
        UpdateChildGuardianRequest(
            child_id=link.child_id,
            guardian_id=link.guardian_id,
            authorized_pickup=True,
        ),
        repository,
    )

    assert link.relationship == "Uncle"
    assert link.authorized_pickup is True
    assert repository.saved_links == [link]


def test_update_child_guardian_rejects_nonexistent_link() -> None:
    link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=uuid4(),
        relationship="Uncle",
        authorized_pickup=False,
    )

    repository = FakeUpdateChildGuardianRepository(link)

    with pytest.raises(ChildGuardianNotFoundError):
        update_child_guardian(
            UpdateChildGuardianRequest(
                child_id=link.child_id,
                guardian_id=uuid4(),
                authorized_pickup=True,
            ),
            repository,
        )

    assert link.relationship == "Uncle"
    assert link.authorized_pickup is False
    assert repository.saved_links == []
