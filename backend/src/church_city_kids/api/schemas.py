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


class CreateRoomBody(BaseModel):
    name: str


class CreateRoomResponse(BaseModel):
    room_id: UUID


class RoomResponse(BaseModel):
    id: UUID
    name: str


class CreateSessionBody(BaseModel):
    service_id: UUID
    room_id: UUID
    name: str
    min_age_years: int
    max_age_years: int


class CreateSessionResponse(BaseModel):
    session_id: UUID


class CheckInBody(BaseModel):
    child_id: UUID
    session_id: UUID
    occurred_at: datetime


class CheckInResponse(BaseModel):
    attendance_id: UUID
