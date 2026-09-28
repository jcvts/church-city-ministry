from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from church_city_kids.infrastructure.persistence.base import Base


class FamilyModel(Base):
    __tablename__ = "families"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GuardianModel(Base):
    __tablename__ = "guardians"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    family_id: Mapped[UUID] = mapped_column(
        ForeignKey("families.id"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ChildModel(Base):
    __tablename__ = "children"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    family_id: Mapped[UUID] = mapped_column(
        ForeignKey("families.id"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ChildGuardianModel(Base):
    __tablename__ = "child_guardians"
    __table_args__ = (
        UniqueConstraint(
            "child_id",
            "guardian_id",
            name="uq_child_guardians_child_guardian",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id"),
        nullable=False,
    )
    guardian_id: Mapped[UUID] = mapped_column(
        ForeignKey("guardians.id"),
        nullable=False,
    )
    relationship: Mapped[str | None] = mapped_column(String, nullable=True)
    authorized_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False)


class VolunteerModel(Base):
    __tablename__ = "volunteers"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ServiceModel(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_services_valid_schedule",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RoomModel(Base):
    __tablename__ = "rooms"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SessionModel(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "min_age_years >= 0",
            name="ck_sessions_min_age_nonnegative",
        ),
        CheckConstraint(
            "max_age_years >= 0",
            name="ck_sessions_max_age_nonnegative",
        ),
        CheckConstraint(
            "min_age_years <= max_age_years",
            name="ck_sessions_valid_age_range",
        ),
        UniqueConstraint(
            "service_id",
            "room_id",
            name="uq_sessions_service_room",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
    )
    room_id: Mapped[UUID] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    min_age_years: Mapped[int] = mapped_column(nullable=False)
    max_age_years: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)


class VolunteerAssignmentModel(Base):
    __tablename__ = "volunteer_assignments"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "volunteer_id",
            name="uq_volunteer_assignments_session_volunteer",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id"),
        nullable=False,
    )
    volunteer_id: Mapped[UUID] = mapped_column(
        ForeignKey("volunteers.id"),
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(String, nullable=True)


class AttendanceModel(Base):
    __tablename__ = "attendances"
    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at >= checked_in_at",
            name="ck_attendances_valid_checkout",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("sessions.id"),
        nullable=False,
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class PagerModel(Base):
    __tablename__ = "pagers"
    __table_args__ = (
        UniqueConstraint(
            "code",
            name="uq_pagers_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class PagerAssignmentModel(Base):
    __tablename__ = "pager_assignments"
    __table_args__ = (
        CheckConstraint(
            "released_at IS NULL OR released_at >= assigned_at",
            name="ck_pager_assignments_valid_release",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    pager_id: Mapped[UUID] = mapped_column(
        ForeignKey("pagers.id"),
        nullable=False,
    )
    attendance_id: Mapped[UUID] = mapped_column(
        ForeignKey("attendances.id"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
