from uuid import UUID, uuid4

import pytest

from church_city_kids.application.remove_child_guardian import (
    ChildGuardianNotFoundError,
    RemoveChildGuardianRequest,
    remove_child_guardian,
)
from church_city_kids.domain.people import ChildGuardian


class FakeRemoveChildGuardianRepository:
    def __init__(self, links: list[ChildGuardian]) -> None:
        self.links = links

    def get_child_guardian(
        self,
        child_id: UUID,
        guardian_id: UUID,
    ) -> ChildGuardian | None:
        return next(
            (
                link
                for link in self.links
                if link.child_id == child_id
                and link.guardian_id == guardian_id
            ),
            None,
        )

    def delete_child_guardian(self, link: ChildGuardian) -> None:
        self.links.remove(link)


def test_remove_existing_child_guardian() -> None:
    guardian_id = uuid4()

    first_link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=guardian_id,
        relationship="Uncle",
        authorized_pickup=True,
    )

    second_link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=guardian_id,
        relationship="Uncle",
        authorized_pickup=True,
    )

    repository = FakeRemoveChildGuardianRepository(
        [first_link, second_link]
    )

    remove_child_guardian(
        RemoveChildGuardianRequest(
            child_id=first_link.child_id,
            guardian_id=guardian_id,
        ),
        repository,
    )

    assert first_link not in repository.links
    assert second_link in repository.links
    assert len(repository.links) == 1


def test_remove_child_guardian_rejects_nonexistent_link() -> None:
    guardian_id = uuid4()

    existing_link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=guardian_id,
        relationship="Uncle",
        authorized_pickup=True,
    )

    repository = FakeRemoveChildGuardianRepository(
        [existing_link]
    )

    with pytest.raises(ChildGuardianNotFoundError):
        remove_child_guardian(
            RemoveChildGuardianRequest(
                child_id=uuid4(),
                guardian_id=guardian_id,
            ),
            repository,
        )

    assert repository.links == [existing_link]
    assert existing_link.authorized_pickup is True
