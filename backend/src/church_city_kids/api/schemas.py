from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class RegisterChildBody(BaseModel):
    child_name: str
    birth_date: date
    guardian_name: str
    guardian_phone: str | None = None
    relationship: str | None = None


class RegisterChildResponse(BaseModel):
    family_id: UUID
    child_id: UUID
    guardian_id: UUID


class CreateServiceBody(BaseModel):
    name: str
    starts_at: datetime
    ends_at: datetime | None = None


class CreateServiceResponse(BaseModel):
    service_id: UUID
 