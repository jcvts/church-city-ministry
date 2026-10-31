from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, StrictBool, model_validator


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


class ChildResponse(BaseModel):
    id: UUID
    family_id: UUID
    full_name: str
    birth_date: date


class GuardianDetailResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str | None
    relationship: str | None
    authorized_pickup: bool
    is_active: bool


class ChildDetailsResponse(BaseModel):
    id: UUID
    family_id: UUID
    full_name: str
    birth_date: date
    guardians: list[GuardianDetailResponse]


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


class CheckOutBody(BaseModel):
    attendance_id: UUID
    guardian_id: UUID
    occurred_at: datetime


class CheckOutResponse(BaseModel):
    attendance_id: UUID


class LoginBody(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpdateMinistrySettingsBody(BaseModel):
    pager_required: StrictBool


class AddChildGuardianBody(BaseModel):
    guardian_id: UUID | None = None
    full_name: str | None = None
    phone: str | None = None
    relationship: str | None = None
    authorized_pickup: bool = False

    @model_validator(mode="after")
    def validate_guardian_input(self) -> "AddChildGuardianBody":
        has_guardian_id = self.guardian_id is not None
        has_full_name = bool(self.full_name and self.full_name.strip())

        if has_guardian_id == has_full_name:
            raise ValueError(
                "Provide either guardian_id or full_name, but not both"
            )

        if has_guardian_id and self.phone is not None:
            raise ValueError(
                "Phone can only be provided for a new guardian"
            )

        return self


class AddChildGuardianResponse(BaseModel):
    link_id: UUID
