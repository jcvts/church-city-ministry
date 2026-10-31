from uuid import uuid4

from church_city_kids.domain.people import ChildGuardian, update_child_guardian


def test_update_child_guardian_relationship_and_pickup_authorization() -> None:
    child_id = uuid4()
    guardian_id = uuid4()

    link = ChildGuardian(
        child_id=child_id,
        guardian_id=guardian_id,
        relationship="Uncle",
        authorized_pickup=False,
    )

    update_child_guardian(
        link,
        relationship="Grandfather",
        authorized_pickup=True,
    )

    assert link.child_id == child_id
    assert link.guardian_id == guardian_id
    assert link.relationship == "Grandfather"
    assert link.authorized_pickup is True


def test_update_child_guardian_only_pickup_authorization() -> None:
    link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=uuid4(),
        relationship="Uncle",
        authorized_pickup=False,
    )

    update_child_guardian(
        link,
        authorized_pickup=True,
    )

    assert link.relationship == "Uncle"
    assert link.authorized_pickup is True


def test_update_child_guardian_clears_relationship() -> None:
    link = ChildGuardian(
        child_id=uuid4(),
        guardian_id=uuid4(),
        relationship="Uncle",
        authorized_pickup=True,
    )

    update_child_guardian(
        link,
        relationship=None,
    )

    assert link.relationship is None
    assert link.authorized_pickup is True
