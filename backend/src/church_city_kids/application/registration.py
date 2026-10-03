from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class RegisterChildRequest:
    child_name: str
    birth_date: date
    guardian_name: str
    guardian_phone: str | None = None
    relationship: str | None = None


@dataclass(frozen=True)
class RegisterChildResult:
    family_id: UUID
    child_id: UUID
    guardian_id: UUID
