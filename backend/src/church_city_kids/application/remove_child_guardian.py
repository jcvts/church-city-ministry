from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import ChildGuardian


@dataclass(frozen=True)
class RemoveChildGuardianRequest:
    child_id: UUID
    guardian_id: UUID


class RemoveChildGuardianRepository(Protocol):
    def get_child_guardian(
        self,
        child_id: UUID,
        guardian_id: UUID,
    ) -> ChildGuardian | None: ...

    def delete_child_guardian(
        self,
        link: ChildGuardian,
    ) -> None: ...


class ChildGuardianNotFoundError(Exception):
    pass


def remove_child_guardian(
    request: RemoveChildGuardianRequest,
    repository: RemoveChildGuardianRepository,
) -> None:
    link = repository.get_child_guardian(
        request.child_id,
        request.guardian_id,
    )

    if link is None:
        raise ChildGuardianNotFoundError()

    repository.delete_child_guardian(link)
