from datetime import date, datetime, time
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool, model_validator


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
    min_age_years: int | None = None
    max_age_years: int | None = None


class UpdateRoomBody(BaseModel):
    name: str | None = None
    min_age_years: int | None = None
    max_age_years: int | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "UpdateRoomBody":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "name" in self.model_fields_set:
            if self.name is None or not self.name.strip():
                raise ValueError("Room name cannot be blank")

        for field_name in ("min_age_years", "max_age_years"):
            value = getattr(self, field_name)

            if field_name in self.model_fields_set:
                if value is not None and value < 0:
                    raise ValueError(f"Invalid {field_name}")

        return self


class CreateRoomResponse(BaseModel):
    room_id: UUID


class RoomResponse(BaseModel):
    id: UUID
    name: str
    min_age_years: int | None = None
    max_age_years: int | None = None


class CreateSessionBody(BaseModel):
    service_id: UUID
    room_id: UUID
    name: str
    min_age_years: int
    max_age_years: int


class CreateSessionResponse(BaseModel):
    session_id: UUID


class CreateUserBody(BaseModel):
    username: str
    password: str


class CreateUserResponse(BaseModel):
    id: UUID
    username: str
    role: Literal["admin", "volunteer"]
    is_active: bool


class UpdateUserStatusBody(BaseModel):
    is_active: bool


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class UpdateUserStatusResponse(BaseModel):
    id: UUID
    username: str
    role: Literal["admin", "volunteer"]
    is_active: bool


class ListUserResponse(BaseModel):
    id: UUID
    username: str
    role: Literal["admin", "volunteer"]
    is_active: bool


class CreateVolunteerBody(BaseModel):
    full_name: str


class CreateVolunteerResponse(BaseModel):
    id: UUID
    full_name: str
    is_active: bool


class ListVolunteerResponse(BaseModel):
    id: UUID
    full_name: str
    is_active: bool


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
            raise ValueError("Provide either guardian_id or full_name, but not both")

        if has_guardian_id and self.phone is not None:
            raise ValueError("Phone can only be provided for a new guardian")

        return self


class AddChildGuardianResponse(BaseModel):
    link_id: UUID


class UpdateChildGuardianBody(BaseModel):
    relationship: str | None = None
    authorized_pickup: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "UpdateChildGuardianBody":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if (
            "authorized_pickup" in self.model_fields_set
            and self.authorized_pickup is None
        ):
            raise ValueError("authorized_pickup cannot be null")

        return self


class UpdateChildBody(BaseModel):
    full_name: str | None = None
    birth_date: date | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "UpdateChildBody":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "full_name" in self.model_fields_set:
            if self.full_name is None or not self.full_name.strip():
                raise ValueError("Child name cannot be blank")

        if "birth_date" in self.model_fields_set and self.birth_date is None:
            raise ValueError("Birth date cannot be null")

        return self


class UpdateGuardianBody(BaseModel):
    full_name: str | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "UpdateGuardianBody":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "full_name" in self.model_fields_set:
            if self.full_name is None or not self.full_name.strip():
                raise ValueError("Guardian name cannot be blank")

        return self


class UpdateFamilyBody(BaseModel):
    is_active: bool


class UpdateVolunteerBody(BaseModel):
    full_name: str | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "UpdateVolunteerBody":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "full_name" in self.model_fields_set:
            if self.full_name is None or not self.full_name.strip():
                raise ValueError("Volunteer name cannot be blank")

        return self


class AssignVolunteerBody(BaseModel):
    volunteer_id: UUID
    role: str | None = None


class AssignVolunteerResponse(BaseModel):
    assignment_id: UUID


class ListVolunteerAssignmentResponse(BaseModel):
    assignment_id: UUID
    service_id: UUID
    session_id: UUID
    volunteer_id: UUID
    volunteer_name: str
    role: str | None


class CreateRecurringServiceScheduleBody(BaseModel):
    name: str | None = None
    weekday: int = Field(ge=0, le=6)
    starts_at: time
    ends_at: time

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("End time must be after start time")
        return self


class UpdateRecurringServiceScheduleBody(BaseModel):
    name: str | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    starts_at: time | None = None
    ends_at: time | None = None
    is_active: bool | None = None
