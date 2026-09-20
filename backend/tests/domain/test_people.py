from datetime import date

import pytest

from church_city_kids.domain.errors import DuplicateChildGuardianError
from church_city_kids.domain.people import ChildGuardian, link_child_guardian
from tests.domain.factories import (
    make_child,
    make_family,
    make_guardian,
    make_volunteer,
)


def test_guardian_can_be_created_without_phone() -> None:
    family = make_family()
    guardian = make_guardian(family)
    assert guardian.phone is None
    assert guardian.family_id == family.id


def test_child_guardian_defaults_authorized_pickup() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    guardian = make_guardian(family)
    existing: list[ChildGuardian] = []

    link = link_child_guardian(child, guardian, existing)

    assert link.child_id == child.id
    assert link.guardian_id == guardian.id
    assert link.authorized_pickup is True
    assert link.relationship is None
    assert existing == [link]


def test_child_guardian_can_store_explicit_pickup_authorization() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    guardian = make_guardian(family)
    existing: list[ChildGuardian] = []

    authorized = link_child_guardian(child, guardian, existing, authorized_pickup=True)
    other_family = make_family()
    other_guardian = make_guardian(other_family)
    unauthorized = link_child_guardian(
        child,
        other_guardian,
        existing,
        authorized_pickup=False,
        relationship="aunt",
    )

    assert authorized.authorized_pickup is True
    assert unauthorized.authorized_pickup is False
    assert unauthorized.relationship == "aunt"


def test_duplicate_child_guardian_link_is_rejected() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    guardian = make_guardian(family, phone="11999999999")
    existing: list[ChildGuardian] = []
    link_child_guardian(child, guardian, existing)

    with pytest.raises(DuplicateChildGuardianError) as exc_info:
        link_child_guardian(child, guardian, existing)

    message = str(exc_info.value)
    assert guardian.full_name not in message
    assert guardian.phone is not None
    assert guardian.phone not in message


def test_people_can_be_deactivated() -> None:
    family = make_family()
    child = make_child(family, birth_date=date(2021, 1, 1))
    guardian = make_guardian(family)
    volunteer = make_volunteer()

    family.deactivate()
    child.deactivate()
    guardian.deactivate()
    volunteer.deactivate()

    assert family.is_active is False
    assert child.is_active is False
    assert guardian.is_active is False
    assert volunteer.is_active is False
