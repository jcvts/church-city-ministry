from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from church_city_kids.domain.people import Guardian

_UNSET = object()


@dataclass(frozen=True)
class UpdateGuardianRequest:
    guardian_id: UUID
    full_name: str | object = _UNSET
    phone: str | None | object = _UNSET


class UpdateGuardianRepository(Protocol):
    def get_guardian(self, guardian_id: UUID) -> Guardian | None: ...

    def save_guardian(self, guardian: Guardian) -> None: ...


class GuardianNotFoundError(Exception):
    pass


def update_guardian(
    request: UpdateGuardianRequest,
    repository: UpdateGuardianRepository,
) -> None:
    if request.full_name is _UNSET and request.phone is _UNSET:
        raise ValueError("At least one field must be provided")

    if request.full_name is not _UNSET:
        if not isinstance(request.full_name, str):
            raise ValueError("Invalid guardian name")
        if not request.full_name.strip():
            raise ValueError("Guardian name cannot be blank")

    if request.phone is not _UNSET:
        if request.phone is not None and not isinstance(request.phone, str):
            raise ValueError("Invalid guardian phone")

    guardian = repository.get_guardian(request.guardian_id)

    if guardian is None:
        raise GuardianNotFoundError()

    if isinstance(request.full_name, str):
        guardian.full_name = request.full_name.strip()

    if request.phone is None or isinstance(request.phone, str):
        guardian.phone = request.phone

    repository.save_guardian(guardian)
