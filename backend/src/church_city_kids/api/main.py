from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import (
    engine,
    get_db_session,
    get_jwt_token_service,
    require_admin,
    require_bearer_token,
)
from church_city_kids.api.schemas import (
    AddChildGuardianBody,
    AddChildGuardianResponse,
    AssignVolunteerBody,
    AssignVolunteerResponse,
    ChangePasswordBody,
    CheckInBody,
    CheckInResponse,
    CheckOutBody,
    CheckOutResponse,
    ChildDetailsResponse,
    ChildResponse,
    CreateRecurringServiceScheduleBody,
    CreateRoomBody,
    CreateRoomResponse,
    CreateServiceBody,
    CreateServiceResponse,
    CreateSessionBody,
    CreateSessionResponse,
    CreateUserBody,
    CreateUserResponse,
    CreateVolunteerBody,
    CreateVolunteerResponse,
    GuardianDetailResponse,
    ListUserResponse,
    ListVolunteerAssignmentResponse,
    ListVolunteerResponse,
    LoginBody,
    LoginResponse,
    RegisterChildBody,
    RegisterChildResponse,
    RoomResponse,
    UpdateChildBody,
    UpdateChildGuardianBody,
    UpdateFamilyBody,
    UpdateGuardianBody,
    UpdateMinistrySettingsBody,
    UpdateRecurringServiceScheduleBody,
    UpdateRoomBody,
    UpdateUserStatusBody,
    UpdateUserStatusResponse,
    UpdateVolunteerBody,
)
from church_city_kids.application.add_child_guardian import (
    AddChildGuardianRequest,
    GuardianNotFoundError,
    add_child_guardian,
)
from church_city_kids.application.add_child_guardian import (
    ChildNotFoundError as AddGuardianChildNotFoundError,
)
from church_city_kids.application.assign_volunteer import (
    AssignVolunteerRequest,
    assign_volunteer,
)
from church_city_kids.application.assign_volunteer import (
    SessionNotFoundError as AssignVolunteerSessionNotFoundError,
)
from church_city_kids.application.assign_volunteer import (
    VolunteerNotFoundError as AssignVolunteerNotFoundError,
)
from church_city_kids.application.authenticate_user import authenticate_user
from church_city_kids.application.change_password import (
    InvalidCurrentPasswordError,
    change_password,
)
from church_city_kids.application.change_password import (
    UserNotFoundError as ChangePasswordUserNotFoundError,
)
from church_city_kids.application.check_in import (
    CheckInRequest,
    ChildNotFoundError,
    SessionNotFoundError,
    check_in_child,
)
from church_city_kids.application.check_out import (
    AttendanceNotFoundError,
    CheckOutRequest,
    check_out_child,
)
from church_city_kids.application.create_room import (
    CreateRoomRequest,
    create_room,
)
from church_city_kids.application.create_service import (
    CreateServiceRequest,
    RoomAgeRangeNotConfiguredError,
    create_service,
)
from church_city_kids.application.create_session import (
    CreateSessionRequest,
    RoomNotFoundError,
    ServiceNotFoundError,
    create_session,
)
from church_city_kids.application.create_user import (
    CreateUserRequest,
    UsernameAlreadyExistsError,
    create_user,
)
from church_city_kids.application.create_volunteer import (
    CreateVolunteerRequest,
    create_volunteer,
)
from church_city_kids.application.generate_recurring_services import (
    RecurringServiceSchedule,
    generate_recurring_services,
)
from church_city_kids.application.get_child_attendance_history import (
    get_child_attendance_history,
)
from church_city_kids.application.get_child_details import get_child_details
from church_city_kids.application.get_family_details import (
    get_family_details,
)
from church_city_kids.application.get_guardian_details import (
    get_guardian_details,
)
from church_city_kids.application.list_children import list_children
from church_city_kids.application.list_families import list_families
from church_city_kids.application.list_guardians import list_guardians
from church_city_kids.application.list_rooms import list_rooms
from church_city_kids.application.list_service_attendances import (
    list_service_attendances,
)
from church_city_kids.application.list_users import list_users
from church_city_kids.application.list_volunteer_assignments import (
    ServiceNotFoundError as ListVolunteerAssignmentsServiceNotFoundError,
)
from church_city_kids.application.list_volunteer_assignments import (
    list_volunteer_assignments,
)
from church_city_kids.application.list_volunteers import list_volunteers
from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.application.remove_child_guardian import (
    ChildGuardianNotFoundError as RemoveChildGuardianNotFoundError,
)
from church_city_kids.application.remove_child_guardian import (
    RemoveChildGuardianRequest,
    remove_child_guardian,
)
from church_city_kids.application.remove_volunteer_assignment import (
    VolunteerAssignmentNotFoundError,
    remove_volunteer_assignment,
)
from church_city_kids.application.update_child import (
    ChildNotFoundError as UpdateChildNotFoundError,
)
from church_city_kids.application.update_child import (
    UpdateChildRequest,
    update_child,
)
from church_city_kids.application.update_child_guardian import (
    ChildGuardianNotFoundError,
    UpdateChildGuardianRequest,
    update_child_guardian,
)
from church_city_kids.application.update_family import (
    FamilyNotFoundError as UpdateFamilyNotFoundError,
)
from church_city_kids.application.update_family import (
    UpdateFamilyRequest,
    update_family,
)
from church_city_kids.application.update_guardian import (
    GuardianNotFoundError as UpdateGuardianNotFoundError,
)
from church_city_kids.application.update_guardian import (
    UpdateGuardianRequest,
    update_guardian,
)
from church_city_kids.application.update_room import (
    RoomNotFoundError as UpdateRoomNotFoundError,
)
from church_city_kids.application.update_room import (
    UpdateRoomRequest,
    update_room,
)
from church_city_kids.application.update_user_status import (
    UserNotFoundError,
    update_user_status,
)
from church_city_kids.application.update_volunteer import (
    UpdateVolunteerRequest,
    update_volunteer,
)
from church_city_kids.application.update_volunteer import (
    VolunteerNotFoundError as UpdateVolunteerNotFoundError,
)
from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    CheckOutBeforeCheckInError,
    ChildAgeOutOfRangeError,
    ChildAlreadyCheckedInError,
    ChildInactiveError,
    DuplicateChildGuardianError,
    FamilyInactiveError,
    GuardianNotAuthorizedForPickupError,
    InvalidAgeRangeError,
    RoomAlreadyAssignedInServiceError,
    RoomInactiveError,
    RoomNameAlreadyExistsError,
    SessionNotOpenError,
    VolunteerAlreadyAssignedInServiceError,
    VolunteerInactiveError,
)
from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.automatic_backup import (
    AutomaticBackupManager,
)
from church_city_kids.infrastructure.persistence.database_config import (
    get_database_path,
)
from church_city_kids.infrastructure.persistence.models import (
    RecurringServiceScheduleModel,
    ServiceModel,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyAddChildGuardianRepository,
    SqlAlchemyAssignVolunteerRepository,
    SqlAlchemyCheckInRepository,
    SqlAlchemyCheckOutRepository,
    SqlAlchemyChildAttendanceHistoryRepository,
    SqlAlchemyCreateRoomRepository,
    SqlAlchemyCreateServiceRepository,
    SqlAlchemyCreateSessionRepository,
    SqlAlchemyGetChildDetailsRepository,
    SqlAlchemyGetFamilyDetailsRepository,
    SqlAlchemyGetGuardianDetailsRepository,
    SqlAlchemyListChildrenRepository,
    SqlAlchemyListFamiliesRepository,
    SqlAlchemyListGuardiansRepository,
    SqlAlchemyListRoomsRepository,
    SqlAlchemyListVolunteerAssignmentsRepository,
    SqlAlchemyMinistrySettingsRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemyRemoveChildGuardianRepository,
    SqlAlchemyRemoveVolunteerAssignmentRepository,
    SqlAlchemyServiceAttendanceRepository,
    SqlAlchemyUpdateChildGuardianRepository,
    SqlAlchemyUpdateChildRepository,
    SqlAlchemyUpdateFamilyRepository,
    SqlAlchemyUpdateGuardianRepository,
    SqlAlchemyUpdateRoomRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyVolunteerRepository,
)
from church_city_kids.infrastructure.security.config import get_jwt_secret_key
from church_city_kids.infrastructure.security.jwt_tokens import JwtTokenService
from church_city_kids.infrastructure.security.passwords import PasswordHasher


def generate_todays_services(
    engine: Engine,
    target_date: date,
) -> None:
    with Session(engine) as db_session:
        schedules = db_session.scalars(
            select(RecurringServiceScheduleModel).where(
                RecurringServiceScheduleModel.is_active.is_(True),
                RecurringServiceScheduleModel.weekday == target_date.weekday(),
            )
        ).all()

        if not schedules:
            return

        recurring_schedules = [
            RecurringServiceSchedule(
                id=schedule.id,
                name=schedule.name,
                weekday=schedule.weekday,
                starts_at=schedule.starts_at,
                ends_at=schedule.ends_at,
            )
            for schedule in schedules
        ]

        repository = SqlAlchemyCreateServiceRepository(db_session)

        try:
            generate_recurring_services(
                target_date,
                recurring_schedules,
                repository,
            )
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_jwt_secret_key()

    backup_manager = getattr(app.state, "backup_manager", None)

    if backup_manager is None:
        database_path = get_database_path()

        backup_manager = AutomaticBackupManager(
            database_path=database_path,
            backup_directory=database_path.parent / "backups",
        )

    backup_manager.start()

    try:
        generate_todays_services(
            engine,
            date.today(),
        )
        yield
    finally:
        backup_manager.stop()


app = FastAPI(
    title="Church City Kids API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/children",
    response_model=RegisterChildResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_child_endpoint(
    body: RegisterChildBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> RegisterChildResponse:
    repository = SqlAlchemyRegistrationRepository(session)

    try:
        result = register_child(
            RegisterChildRequest(
                child_name=body.child_name,
                birth_date=body.birth_date,
                guardian_name=body.guardian_name,
                guardian_phone=body.guardian_phone,
                relationship=body.relationship,
            ),
            repository,
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return RegisterChildResponse(
        family_id=result.family_id,
        child_id=result.child_id,
        guardian_id=result.guardian_id,
    )


@app.get(
    "/api/children",
    response_model=list[ChildResponse],
)
def list_children_endpoint(
    name: str,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[ChildResponse]:
    repository = SqlAlchemyListChildrenRepository(session)

    result = list_children(repository, name=name)

    return [
        ChildResponse(
            id=child.id,
            family_id=child.family_id,
            full_name=child.full_name,
            birth_date=child.birth_date,
        )
        for child in result
    ]


@app.get(
    "/api/children/{child_id}",
    response_model=ChildDetailsResponse,
)
def get_child_details_endpoint(
    child_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> ChildDetailsResponse:
    repository = SqlAlchemyGetChildDetailsRepository(session)

    result = get_child_details(repository, child_id=child_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    return ChildDetailsResponse(
        id=result.id,
        family_id=result.family_id,
        full_name=result.full_name,
        birth_date=result.birth_date,
        guardians=[
            GuardianDetailResponse(
                id=guardian.id,
                full_name=guardian.full_name,
                phone=guardian.phone,
                relationship=guardian.relationship,
                authorized_pickup=guardian.authorized_pickup,
                is_active=guardian.is_active,
            )
            for guardian in result.guardians
        ],
    )


@app.get("/api/children/{child_id}/attendance")
def get_child_attendance_history_endpoint(
    child_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[dict[str, str | None]]:
    child = SqlAlchemyGetChildDetailsRepository(session).get_child(child_id)

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    repository = SqlAlchemyChildAttendanceHistoryRepository(session)
    history = get_child_attendance_history(child_id, repository)

    return [
        {
            "attendance_id": str(item.attendance_id),
            "child_id": str(item.child_id),
            "service_name": item.service_name,
            "service_starts_at": item.service_starts_at.isoformat(),
            "room_name": item.room_name,
            "checked_in_at": item.checked_in_at.isoformat(),
            "checked_out_at": (
                item.checked_out_at.isoformat()
                if item.checked_out_at is not None
                else None
            ),
            "checked_out_by_guardian_name": item.checked_out_by_guardian_name,
        }
        for item in history
    ]


@app.get("/api/families")
def list_families_endpoint(
    name: str,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[dict[str, str | bool]]:
    repository = SqlAlchemyListFamiliesRepository(session)

    families = list_families(
        repository,
        name=name,
    )

    return [
        {
            "id": str(family.id),
            "is_active": family.is_active,
        }
        for family in families
    ]


@app.get("/api/families/{family_id}")
def get_family_details_endpoint(
    family_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> dict[str, object]:
    repository = SqlAlchemyGetFamilyDetailsRepository(session)

    family = get_family_details(
        repository,
        family_id=family_id,
    )

    if family is None:
        raise HTTPException(
            status_code=404,
            detail="Family not found",
        )

    return {
        "id": str(family.id),
        "is_active": family.is_active,
        "children": [
            {
                "id": str(child.id),
                "full_name": child.full_name,
                "birth_date": child.birth_date.isoformat(),
                "is_active": child.is_active,
            }
            for child in family.children
        ],
        "guardians": [
            {
                "id": str(guardian.id),
                "full_name": guardian.full_name,
                "phone": guardian.phone,
                "is_active": guardian.is_active,
            }
            for guardian in family.guardians
        ],
    }


@app.patch("/api/families/{family_id}", status_code=status.HTTP_200_OK)
def update_family_endpoint(
    family_id: UUID,
    body: UpdateFamilyBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    repository = SqlAlchemyUpdateFamilyRepository(session)

    try:
        update_family(
            UpdateFamilyRequest(
                family_id=family_id,
                is_active=body.is_active,
            ),
            repository,
        )
        session.commit()

    except UpdateFamilyNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Family not found",
        ) from exc

    except Exception:
        session.rollback()
        raise

    return {"status": "updated"}


@app.get("/api/guardians")
def list_guardians_endpoint(
    name: str,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[dict[str, object]]:
    repository = SqlAlchemyListGuardiansRepository(session)

    guardians = list_guardians(
        repository,
        name=name,
    )

    return [
        {
            "id": str(guardian.id),
            "family_id": str(guardian.family_id),
            "full_name": guardian.full_name,
            "phone": guardian.phone,
            "is_active": guardian.is_active,
        }
        for guardian in guardians
    ]


@app.get("/api/guardians/{guardian_id}")
def get_guardian_details_endpoint(
    guardian_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> dict[str, object]:
    repository = SqlAlchemyGetGuardianDetailsRepository(session)

    guardian = get_guardian_details(
        repository,
        guardian_id=guardian_id,
    )

    if guardian is None:
        raise HTTPException(
            status_code=404,
            detail="Guardian not found",
        )

    return {
        "id": str(guardian.id),
        "family_id": str(guardian.family_id),
        "full_name": guardian.full_name,
        "phone": guardian.phone,
        "is_active": guardian.is_active,
        "children": [
            {
                "id": str(child.id),
                "family_id": str(child.family_id),
                "full_name": child.full_name,
                "birth_date": child.birth_date.isoformat(),
                "is_active": child.is_active,
                "relationship": child.relationship,
                "authorized_pickup": child.authorized_pickup,
            }
            for child in guardian.children
        ],
    }


@app.post(
    "/api/children/{child_id}/guardians",
    response_model=AddChildGuardianResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_child_guardian_endpoint(
    child_id: UUID,
    body: AddChildGuardianBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> AddChildGuardianResponse:
    repository = SqlAlchemyAddChildGuardianRepository(session)

    try:
        result = add_child_guardian(
            AddChildGuardianRequest(
                child_id=child_id,
                guardian_id=body.guardian_id,
                full_name=body.full_name,
                phone=body.phone,
                relationship=body.relationship,
                authorized_pickup=body.authorized_pickup,
            ),
            repository,
        )
        session.commit()

    except AddGuardianChildNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        ) from exc

    except GuardianNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardian not found",
        ) from exc

    except DuplicateChildGuardianError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Guardian already linked to child",
        ) from exc

    except Exception:
        session.rollback()
        raise

    return AddChildGuardianResponse(link_id=result.link_id)


@app.patch(
    "/api/children/{child_id}/guardians/{guardian_id}",
    status_code=status.HTTP_200_OK,
)
def update_child_guardian_endpoint(
    child_id: UUID,
    guardian_id: UUID,
    body: UpdateChildGuardianBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> dict[str, str]:
    repository = SqlAlchemyUpdateChildGuardianRepository(session)

    updates = body.model_dump(exclude_unset=True)

    try:
        update_child_guardian(
            UpdateChildGuardianRequest(
                child_id=child_id,
                guardian_id=guardian_id,
                **updates,
            ),
            repository,
        )
        session.commit()

    except ChildGuardianNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Child guardian link not found",
        ) from exc

    except Exception:
        session.rollback()
        raise

    return {"status": "updated"}


@app.delete(
    "/api/children/{child_id}/guardians/{guardian_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_child_guardian_endpoint(
    child_id: UUID,
    guardian_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> None:
    repository = SqlAlchemyRemoveChildGuardianRepository(session)

    try:
        remove_child_guardian(
            RemoveChildGuardianRequest(
                child_id=child_id,
                guardian_id=guardian_id,
            ),
            repository,
        )
        session.commit()

    except RemoveChildGuardianNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child guardian link not found",
        ) from exc

    except Exception:
        session.rollback()
        raise


@app.get("/api/services")
def list_services_endpoint(
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
    date_filter: Annotated[date | None, Query(alias="date")] = None,
) -> list[dict[str, str | None]]:
    statement = select(ServiceModel)

    if date_filter is not None:
        start = datetime.combine(date_filter, time.min)
        end = start + timedelta(days=1)

        statement = statement.where(
            ServiceModel.starts_at >= start,
            ServiceModel.starts_at < end,
        )

    statement = statement.order_by(ServiceModel.starts_at, ServiceModel.id)

    services = session.scalars(statement).all()

    return [
        {
            "service_id": str(service.id),
            "name": service.name,
            "starts_at": service.starts_at.isoformat(),
            "ends_at": (
                service.ends_at.isoformat() if service.ends_at is not None else None
            ),
        }
        for service in services
    ]


@app.post(
    "/api/services",
    response_model=CreateServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_endpoint(
    body: CreateServiceBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> CreateServiceResponse:
    repository = SqlAlchemyCreateServiceRepository(session)

    try:
        result = create_service(
            CreateServiceRequest(
                name=body.name,
                starts_at=body.starts_at,
                ends_at=body.ends_at,
            ),
            repository,
        )

        session.commit()
    except RoomAgeRangeNotConfiguredError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception:
        session.rollback()
        raise

    return CreateServiceResponse(
        service_id=result.service_id,
    )


@app.get("/api/services/{service_id}/attendances")
def get_service_attendances(
    service_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[dict[str, str | None]]:

    service = session.get(ServiceModel, service_id)

    if service is None:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    repository = SqlAlchemyServiceAttendanceRepository(session)

    attendances = list_service_attendances(
        service_id,
        repository,
    )

    return [
        {
            "attendance_id": str(item.attendance_id),
            "service_id": str(item.service_id),
            "child_id": str(item.child_id),
            "child_name": item.child_name,
            "room_id": str(item.room_id),
            "room_name": item.room_name,
            "checked_in_at": item.checked_in_at.isoformat(),
            "checked_out_at": (
                item.checked_out_at.isoformat()
                if item.checked_out_at is not None
                else None
            ),
        }
        for item in attendances
    ]


@app.get(
    "/api/services/{service_id}/volunteers",
    response_model=list[ListVolunteerAssignmentResponse],
    status_code=status.HTTP_200_OK,
)
def list_service_volunteers_endpoint(
    service_id: UUID,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_bearer_token),
) -> list[ListVolunteerAssignmentResponse]:
    repository = SqlAlchemyListVolunteerAssignmentsRepository(db_session)

    try:
        assignments = list_volunteer_assignments(
            service_id=service_id,
            repository=repository,
        )
    except ListVolunteerAssignmentsServiceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        ) from exc

    return [
        ListVolunteerAssignmentResponse(
            assignment_id=item.assignment_id,
            service_id=item.service_id,
            session_id=item.session_id,
            volunteer_id=item.volunteer_id,
            volunteer_name=item.volunteer_name,
            role=item.role,
        )
        for item in assignments
    ]


@app.post(
    "/api/rooms",
    response_model=CreateRoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room_endpoint(
    body: CreateRoomBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> CreateRoomResponse:
    repository = SqlAlchemyCreateRoomRepository(session)

    try:
        result = create_room(
            CreateRoomRequest(
                name=body.name,
                min_age_years=body.min_age_years,
                max_age_years=body.max_age_years,
            ),
            repository,
        )

        session.commit()

    except RoomNameAlreadyExistsError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room name already exists",
        ) from None

    except Exception:
        session.rollback()
        raise

    return CreateRoomResponse(room_id=result.room_id)


@app.get(
    "/api/rooms",
    response_model=list[RoomResponse],
)
def list_rooms_endpoint(
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[RoomResponse]:
    repository = SqlAlchemyListRoomsRepository(session)

    result = list_rooms(repository)

    return [
        RoomResponse(
            id=room.id,
            name=room.name,
            min_age_years=room.min_age_years,
            max_age_years=room.max_age_years,
        )
        for room in result
    ]


@app.patch(
    "/api/rooms/{room_id}",
    status_code=status.HTTP_200_OK,
)
def update_room_endpoint(
    room_id: UUID,
    body: UpdateRoomBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, str]:
    repository = SqlAlchemyUpdateRoomRepository(session)
    updates = body.model_dump(exclude_unset=True)

    try:
        update_room(
            UpdateRoomRequest(
                room_id=room_id,
                **updates,
            ),
            repository,
        )

        session.commit()

    except UpdateRoomNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        ) from exc

    except RoomNameAlreadyExistsError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room name already exists",
        ) from exc

    except InvalidAgeRangeError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except Exception:
        session.rollback()
        raise

    return {"status": "updated"}


@app.get("/api/sessions")
def list_sessions_endpoint(
    service_id: UUID,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> list[dict[str, str | int]]:
    repository = SqlAlchemyCreateSessionRepository(db_session)

    if repository.get_service(service_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )

    sessions = repository.get_sessions_for_service(service_id)

    return [
        {
            "session_id": str(item.id),
            "service_id": str(item.service_id),
            "room_id": str(item.room_id),
            "name": item.name,
            "min_age_years": item.min_age_years,
            "max_age_years": item.max_age_years,
            "status": item.status.value,
        }
        for item in sessions
    ]


@app.post(
    "/api/sessions",
    response_model=CreateSessionResponse,
    status_code=201,
)
def create_session_endpoint(
    body: CreateSessionBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> CreateSessionResponse:
    repository = SqlAlchemyCreateSessionRepository(db_session)

    try:
        result = create_session(
            CreateSessionRequest(
                service_id=body.service_id,
                room_id=body.room_id,
                name=body.name,
                min_age_years=body.min_age_years,
                max_age_years=body.max_age_years,
            ),
            repository,
        )

        db_session.commit()

    except ServiceNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        ) from exc

    except RoomNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        ) from exc
    except RoomInactiveError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Room is inactive",
        ) from exc
    except RoomAlreadyAssignedInServiceError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Room already assigned to this service",
        ) from exc
    except InvalidAgeRangeError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=422,
            detail="Invalid age range",
        ) from exc

    except Exception:
        db_session.rollback()
        raise

    return CreateSessionResponse(session_id=result.session_id)


@app.post(
    "/api/sessions/{session_id}/volunteers",
    response_model=AssignVolunteerResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_volunteer_endpoint(
    session_id: UUID,
    body: AssignVolunteerBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_bearer_token),
) -> AssignVolunteerResponse:
    repository = SqlAlchemyAssignVolunteerRepository(db_session)

    try:
        result = assign_volunteer(
            AssignVolunteerRequest(
                session_id=session_id,
                volunteer_id=body.volunteer_id,
                role=body.role,
            ),
            repository,
        )
        db_session.commit()

    except AssignVolunteerSessionNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc

    except AssignVolunteerNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found",
        ) from exc

    except VolunteerInactiveError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer is inactive",
        ) from exc

    except VolunteerAlreadyAssignedInServiceError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer already assigned to this service",
        ) from exc

    except IntegrityError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer assignment conflicts with existing data",
        ) from exc

    except Exception:
        db_session.rollback()
        raise

    return AssignVolunteerResponse(
        assignment_id=result.assignment_id,
    )


@app.delete(
    "/api/volunteer-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_volunteer_assignment_endpoint(
    assignment_id: UUID,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_bearer_token),
) -> None:
    repository = SqlAlchemyRemoveVolunteerAssignmentRepository(db_session)

    try:
        remove_volunteer_assignment(
            assignment_id=assignment_id,
            repository=repository,
        )
        db_session.commit()

    except VolunteerAssignmentNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer assignment not found",
        ) from exc

    except Exception:
        db_session.rollback()
        raise


@app.post(
    "/api/check-ins",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
)
def check_in_child_endpoint(
    body: CheckInBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> CheckInResponse:
    repository = SqlAlchemyCheckInRepository(db_session)

    try:
        result = check_in_child(
            CheckInRequest(
                child_id=body.child_id,
                session_id=body.session_id,
                occurred_at=body.occurred_at,
            ),
            repository,
        )

        db_session.commit()

    except (ChildNotFoundError, SessionNotFoundError) as exc:
        db_session.rollback()

        detail = (
            "Child not found"
            if isinstance(exc, ChildNotFoundError)
            else "Session not found"
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        ) from exc

    except (
        ChildAlreadyCheckedInError,
        SessionNotOpenError,
        ChildInactiveError,
        FamilyInactiveError,
    ) as exc:
        db_session.rollback()

        details = {
            ChildAlreadyCheckedInError: "Child already checked in",
            SessionNotOpenError: "Session is not open",
            ChildInactiveError: "Child is inactive",
            FamilyInactiveError: "Family is inactive",
        }

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=details[type(exc)],
        ) from exc

    except ChildAgeOutOfRangeError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Child age is out of range",
        ) from exc

    except Exception:
        db_session.rollback()
        raise

    return CheckInResponse(attendance_id=result.attendance_id)


@app.post(
    "/api/check-outs",
    response_model=CheckOutResponse,
    status_code=status.HTTP_200_OK,
)
def check_out_child_endpoint(
    body: CheckOutBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> CheckOutResponse:
    repository = SqlAlchemyCheckOutRepository(db_session)

    try:
        result = check_out_child(
            CheckOutRequest(
                attendance_id=body.attendance_id,
                guardian_id=body.guardian_id,
                occurred_at=body.occurred_at,
            ),
            repository,
        )

        db_session.commit()

    except AttendanceNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance not found",
        ) from exc

    except AttendanceAlreadyCheckedOutError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance already checked out",
        ) from exc

    except CheckOutBeforeCheckInError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Check-out cannot occur before check-in",
        ) from exc

    except GuardianNotAuthorizedForPickupError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guardian is not authorized to pick up this child",
        ) from exc

    except Exception:
        db_session.rollback()
        raise

    return CheckOutResponse(attendance_id=result.attendance_id)


@app.get("/api/admin/recurring-services")
def list_recurring_services_endpoint(
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> list[dict[str, object]]:
    schedules = db_session.scalars(
        select(RecurringServiceScheduleModel).order_by(
            RecurringServiceScheduleModel.weekday,
            RecurringServiceScheduleModel.starts_at,
        )
    ).all()

    return [
        {
            "id": schedule.id,
            "name": schedule.name,
            "weekday": schedule.weekday,
            "starts_at": schedule.starts_at.isoformat(),
            "ends_at": schedule.ends_at.isoformat(),
            "is_active": schedule.is_active,
        }
        for schedule in schedules
    ]


@app.get("/api/admin/settings")
def get_ministry_settings_endpoint(
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, bool]:
    repository = SqlAlchemyMinistrySettingsRepository(db_session)
    settings = repository.get()

    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ministry settings not found",
        )

    return {"pager_required": settings.pager_required}


@app.patch("/api/admin/settings")
def update_ministry_settings_endpoint(
    body: UpdateMinistrySettingsBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, bool]:
    repository = SqlAlchemyMinistrySettingsRepository(db_session)
    settings = repository.get()

    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ministry settings not found",
        )

    try:
        settings.pager_required = body.pager_required
        repository.save(settings)
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise

    return {"pager_required": settings.pager_required}


@app.post(
    "/api/admin/recurring-services",
    status_code=status.HTTP_201_CREATED,
)
def create_recurring_service_schedule_endpoint(
    body: CreateRecurringServiceScheduleBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, object]:
    schedule = RecurringServiceScheduleModel(
        name=body.name,
        weekday=body.weekday,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        is_active=True,
    )

    try:
        db_session.add(schedule)
        db_session.commit()
        db_session.refresh(schedule)
    except Exception:
        db_session.rollback()
        raise

    return {
        "id": schedule.id,
        "name": schedule.name,
        "weekday": schedule.weekday,
        "starts_at": schedule.starts_at.isoformat(),
        "ends_at": schedule.ends_at.isoformat(),
        "is_active": schedule.is_active,
    }


@app.patch("/api/admin/recurring-services/{schedule_id}")
def update_recurring_service_schedule_endpoint(
    schedule_id: int,
    body: UpdateRecurringServiceScheduleBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
) -> dict[str, object]:
    schedule = db_session.get(RecurringServiceScheduleModel, schedule_id)

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring service schedule not found",
        )

    updates = body.model_dump(exclude_unset=True)

    if "name" in updates:
        schedule.name = updates["name"]

    if "weekday" in updates:
        if updates["weekday"] is None:
            raise HTTPException(status_code=422, detail="Weekday cannot be null")
        schedule.weekday = updates["weekday"]

    if "starts_at" in updates:
        if updates["starts_at"] is None:
            raise HTTPException(status_code=422, detail="Start time cannot be null")
        schedule.starts_at = updates["starts_at"]

    if "ends_at" in updates:
        if updates["ends_at"] is None:
            raise HTTPException(status_code=422, detail="End time cannot be null")
        schedule.ends_at = updates["ends_at"]

    if "is_active" in updates:
        if updates["is_active"] is None:
            raise HTTPException(status_code=422, detail="Active status cannot be null")
        schedule.is_active = updates["is_active"]

    if schedule.ends_at <= schedule.starts_at:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End time must be after start time",
        )

    try:
        db_session.commit()
        db_session.refresh(schedule)
    except Exception:
        db_session.rollback()
        raise

    return {
        "id": schedule.id,
        "name": schedule.name,
        "weekday": schedule.weekday,
        "starts_at": schedule.starts_at.isoformat(),
        "ends_at": schedule.ends_at.isoformat(),
        "is_active": schedule.is_active,
    }


@app.post("/api/auth/login", response_model=LoginResponse)
def login_endpoint(
    body: LoginBody,
    db_session: Annotated[Session, Depends(get_db_session)],
    token_service: Annotated[
        JwtTokenService,
        Depends(get_jwt_token_service),
    ],
) -> LoginResponse:
    repository = SqlAlchemyUserRepository(db_session)

    user = authenticate_user(
        username=body.username,
        password=body.password,
        repository=repository,
        password_hasher=PasswordHasher(),
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return LoginResponse(
        access_token=token_service.create_access_token(user.id),
    )


@app.patch(
    "/api/children/{child_id}",
    status_code=status.HTTP_200_OK,
)
def update_child_endpoint(
    child_id: UUID,
    body: UpdateChildBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> dict[str, str]:
    repository = SqlAlchemyUpdateChildRepository(session)
    updates = body.model_dump(exclude_unset=True)

    try:
        update_child(
            UpdateChildRequest(
                child_id=child_id,
                **updates,
            ),
            repository,
        )
        session.commit()

    except UpdateChildNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Child not found",
        ) from exc

    except Exception:
        session.rollback()
        raise

    return {"status": "updated"}


@app.patch("/api/guardians/{guardian_id}", status_code=status.HTTP_200_OK)
def update_guardian_endpoint(
    guardian_id: UUID,
    body: UpdateGuardianBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_bearer_token)],
) -> dict[str, str]:
    repository = SqlAlchemyUpdateGuardianRepository(session)
    updates = body.model_dump(exclude_unset=True)

    try:
        update_guardian(
            UpdateGuardianRequest(guardian_id=guardian_id, **updates),
            repository,
        )
        session.commit()
    except UpdateGuardianNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=404,
            detail="Guardian not found",
        ) from exc
    except Exception:
        session.rollback()
        raise

    return {"status": "updated"}


@app.post(
    "/api/volunteers",
    response_model=CreateVolunteerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_volunteer_endpoint(
    body: CreateVolunteerBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> CreateVolunteerResponse:
    repository = SqlAlchemyVolunteerRepository(db_session)

    try:
        volunteer_id = create_volunteer(
            CreateVolunteerRequest(full_name=body.full_name),
            repository,
        )

        db_session.commit()

    except ValueError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return CreateVolunteerResponse(
        id=volunteer_id,
        full_name=body.full_name.strip(),
        is_active=True,
    )


@app.get(
    "/api/volunteers",
    response_model=list[ListVolunteerResponse],
    status_code=status.HTTP_200_OK,
)
def list_volunteers_endpoint(
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_bearer_token),
) -> list[ListVolunteerResponse]:
    repository = SqlAlchemyVolunteerRepository(db_session)

    volunteers = list_volunteers(repository=repository)

    return [
        ListVolunteerResponse(
            id=volunteer.id,
            full_name=volunteer.full_name,
            is_active=volunteer.is_active,
        )
        for volunteer in volunteers
    ]


@app.patch(
    "/api/volunteers/{volunteer_id}",
    status_code=status.HTTP_200_OK,
)
def update_volunteer_endpoint(
    volunteer_id: UUID,
    body: UpdateVolunteerBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> dict[str, str]:
    repository = SqlAlchemyVolunteerRepository(db_session)
    updates = body.model_dump(exclude_unset=True)

    try:
        update_volunteer(
            UpdateVolunteerRequest(
                volunteer_id=volunteer_id,
                **updates,
            ),
            repository,
        )

        db_session.commit()

    except UpdateVolunteerNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volunteer not found",
        ) from exc

    except Exception:
        db_session.rollback()
        raise

    return {"status": "updated"}


@app.get(
    "/api/users",
    response_model=list[ListUserResponse],
    status_code=status.HTTP_200_OK,
)
def list_users_endpoint(
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> list[ListUserResponse]:
    repository = SqlAlchemyUserRepository(db_session)

    users = list_users(repository=repository)

    return [
        ListUserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
        )
        for user in users
    ]


@app.post(
    "/api/users",
    response_model=CreateUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_endpoint(
    body: CreateUserBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> CreateUserResponse:
    repository = SqlAlchemyUserRepository(db_session)

    try:
        user_id = create_user(
            CreateUserRequest(
                username=body.username,
                password=body.password,
            ),
            repository,
            PasswordHasher(),
        )

        db_session.commit()

    except UsernameAlreadyExistsError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return CreateUserResponse(
        id=user_id,
        username=body.username.strip(),
        role="volunteer",
        is_active=True,
    )


@app.patch(
    "/api/users/{user_id}/status",
    response_model=UpdateUserStatusResponse,
    status_code=status.HTTP_200_OK,
)
def update_user_status_endpoint(
    user_id: UUID,
    body: UpdateUserStatusBody,
    db_session: Session = Depends(get_db_session),
    _auth: User = Depends(require_admin),
) -> UpdateUserStatusResponse:
    repository = SqlAlchemyUserRepository(db_session)

    try:
        updated_user = update_user_status(
            user_id=user_id,
            is_active=body.is_active,
            repository=repository,
        )

        db_session.commit()

    except UserNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from exc

    return UpdateUserStatusResponse(
        id=updated_user.id,
        username=updated_user.username,
        role=updated_user.role,
        is_active=updated_user.is_active,
    )


@app.patch(
    "/api/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_own_password_endpoint(
    body: ChangePasswordBody,
    db_session: Session = Depends(get_db_session),
    authenticated_user: User = Depends(require_bearer_token),
) -> None:
    repository = SqlAlchemyUserRepository(db_session)
    hasher = PasswordHasher()

    try:
        change_password(
            user_id=authenticated_user.id,
            current_password=body.current_password,
            new_password=body.new_password,
            repository=repository,
            password_hasher=hasher,
        )
        db_session.commit()

    except InvalidCurrentPasswordError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from exc

    except ChangePasswordUserNotFoundError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        ) from exc

    except ValueError as exc:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
