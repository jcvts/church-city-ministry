from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from church_city_kids.domain.scheduling import normalize_room_name
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


class RecurringServiceScheduleModel(Base):
    __tablename__ = "recurring_service_schedules"
    __table_args__ = (
        CheckConstraint(
            "weekday BETWEEN 0 AND 6",
            name="ck_recurring_schedules_weekday",
        ),
        CheckConstraint(
            "ends_at > starts_at",
            name="ck_recurring_schedules_valid_time",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    weekday: Mapped[int] = mapped_column(nullable=False)
    starts_at: Mapped[time] = mapped_column(Time, nullable=False)
    ends_at: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )


class ServiceModel(Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_services_valid_schedule",
        ),
        UniqueConstraint(
            "recurring_schedule_id",
            "starts_at",
            name="uq_services_recurring_schedule_start",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recurring_schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_service_schedules.id"),
        nullable=True,
    )


class RoomModel(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            """
            (min_age_years IS NULL AND max_age_years IS NULL)
            OR (
                min_age_years IS NOT NULL
                AND max_age_years IS NOT NULL
                AND min_age_years >= 0
                AND max_age_years >= min_age_years
            )
            """,
            name="ck_rooms_valid_age_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        default=lambda context: normalize_room_name(
            context.get_current_parameters()["name"]
        ),
    )
    min_age_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    max_age_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )


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
        Index(
            "uq_sessions_id_service",
            "id",
            "service_id",
            unique=True,
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
        UniqueConstraint(
            "service_id",
            "volunteer_id",
            name="uq_volunteer_assignments_service_volunteer",
        ),
        ForeignKeyConstraint(
            ["session_id", "service_id"],
            ["sessions.id", "sessions.service_id"],
            name="fk_volunteer_assignments_session_service",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id"),
        nullable=False,
    )

    session_id: Mapped[UUID] = mapped_column(
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
    checked_out_by_guardian_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("guardians.id"),
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
        Index(
            "uq_active_pager_assignment",
            "pager_id",
            unique=True,
            sqlite_where=text("released_at IS NULL"),
        ),
        Index(
            "uq_active_family_service_pager",
            "family_id",
            "service_id",
            unique=True,
            sqlite_where=text("released_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    pager_id: Mapped[UUID] = mapped_column(
        ForeignKey("pagers.id"),
        nullable=False,
    )

    family_id: Mapped[UUID] = mapped_column(
        ForeignKey("families.id"),
        nullable=False,
    )

    service_id: Mapped[UUID] = mapped_column(
        ForeignKey("services.id"),
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


class MinistrySettingsModel(Base):
    __tablename__ = "ministry_settings"
    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_ministry_settings_singleton",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    pager_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_username_lower",
            text("lower(username)"),
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="volunteer",
    )
