from datetime import datetime

import pytest

from church_city_kids.domain.errors import (
    PagerAlreadyAssignedError,
    PagerInactiveError,
)
from church_city_kids.domain.pager import Pager, PagerAssignment, assign_pager
from tests.domain.factories import make_family, make_service


def test_assign_pager_to_family_for_service() -> None:
    family = make_family()
    service = make_service()
    pager = Pager(code="012")

    assignment = assign_pager(
        family_id=family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=[],
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    assert assignment.pager_id == pager.id
    assert assignment.family_id == family.id
    assert assignment.service_id == service.id
    assert assignment.is_active
    assert not hasattr(assignment, "attendance_id")


def test_same_pager_cannot_be_assigned_to_different_families() -> None:
    first_family = make_family()
    second_family = make_family()
    service = make_service()
    pager = Pager(code="012")
    assignments: list[PagerAssignment] = []

    assign_pager(
        family_id=first_family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    with pytest.raises(PagerAlreadyAssignedError):
        assign_pager(
            family_id=second_family.id,
            service_id=service.id,
            pager=pager,
            active_assignments=assignments,
            occurred_at=datetime(2026, 9, 20, 9, 52),
        )


def test_family_cannot_have_two_active_pagers_in_same_service() -> None:
    family = make_family()
    service = make_service()
    assignments: list[PagerAssignment] = []
    assigned_at = datetime(2026, 9, 20, 9, 51)

    assign_pager(
        family_id=family.id,
        service_id=service.id,
        pager=Pager(code="012"),
        active_assignments=assignments,
        occurred_at=assigned_at,
    )

    with pytest.raises(PagerAlreadyAssignedError):
        assign_pager(
            family_id=family.id,
            service_id=service.id,
            pager=Pager(code="013"),
            active_assignments=assignments,
            occurred_at=assigned_at,
        )


def test_family_reuses_existing_pager_assignment_in_same_service() -> None:
    family = make_family()
    service = make_service()
    pager = Pager(code="012")
    assignments: list[PagerAssignment] = []

    first = assign_pager(
        family_id=family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    second = assign_pager(
        family_id=family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 55),
    )

    assert second is first
    assert len(assignments) == 1


def test_releasing_pager_assignment_keeps_history() -> None:
    family = make_family()
    service = make_service()
    pager = Pager(code="012")
    assignments: list[PagerAssignment] = []

    assignment = assign_pager(
        family_id=family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    released_at = datetime(2026, 9, 20, 11, 0)
    assignment.release(released_at)

    assert assignment.released_at == released_at
    assert not assignment.is_active
    assert assignment in assignments


def test_inactive_pager_cannot_be_assigned() -> None:
    family = make_family()
    service = make_service()
    pager = Pager(code="012")
    pager.deactivate()

    with pytest.raises(PagerInactiveError):
        assign_pager(
            family_id=family.id,
            service_id=service.id,
            pager=pager,
            active_assignments=[],
            occurred_at=datetime(2026, 9, 20, 9, 51),
        )


def test_released_pager_can_be_assigned_to_another_family() -> None:
    first_family = make_family()
    second_family = make_family()
    service = make_service()
    pager = Pager(code="012")
    assignments: list[PagerAssignment] = []

    first = assign_pager(
        family_id=first_family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    first.release(datetime(2026, 9, 20, 11, 0))

    second = assign_pager(
        family_id=second_family.id,
        service_id=service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 11, 5),
    )

    assert second.id != first.id
    assert second.family_id == second_family.id
    assert len(assignments) == 2
    assert not first.is_active
    assert second.is_active


def test_same_family_cannot_reuse_pager_assigned_to_another_service() -> None:
    family = make_family()
    first_service = make_service()
    second_service = make_service()
    pager = Pager(code="012")
    assignments: list[PagerAssignment] = []

    assign_pager(
        family_id=family.id,
        service_id=first_service.id,
        pager=pager,
        active_assignments=assignments,
        occurred_at=datetime(2026, 9, 20, 9, 51),
    )

    with pytest.raises(PagerAlreadyAssignedError):
        assign_pager(
            family_id=family.id,
            service_id=second_service.id,
            pager=pager,
            active_assignments=assignments,
            occurred_at=datetime(2026, 9, 20, 10, 0),
        )