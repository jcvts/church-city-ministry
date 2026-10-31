from uuid import uuid4

from church_city_kids.domain.people import (
    ChildGuardian,
    remove_child_guardian,
)


def test_remove_child_guardian_removes_only_target_link() -> None:
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

    links = [first_link, second_link]

    remove_child_guardian(
        first_link,
        links,
    )

    assert first_link not in links
    assert second_link in links
    assert len(links) == 1
