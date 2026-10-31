from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import (
    get_db_session,
    get_jwt_token_service,
    require_admin,
    require_bearer_token,
)
from church_city_kids.api.schemas import (
    AddChildGuardianBody,
    AddChildGuardianResponse,
    CheckInBody,
    CheckInResponse,
    CheckOutBody,
    CheckOutResponse,
    ChildDetailsResponse,
    ChildResponse,
    CreateRoomBody,
    CreateRoomResponse,
    CreateServiceBody,
    CreateServiceResponse,
    CreateSessionBody,
    CreateSessionResponse,
    GuardianDetailResponse,
    LoginBody,
    LoginResponse,
    RegisterChildBody,
    RegisterChildResponse,
    RoomResponse,
    UpdateChildGuardianBody,
    UpdateMinistrySettingsBody,
)
from church_city_kids.application.add_child_guardian import (
    AddChildGuardianRequest,
    GuardianNotFoundError,
    add_child_guardian,
)
from church_city_kids.application.add_child_guardian import (
    ChildNotFoundError as AddGuardianChildNotFoundError,
)
from church_city_kids.application.authenticate_user import authenticate_user
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
    create_service,
)
from church_city_kids.application.create_session import (
    CreateSessionRequest,
    RoomNotFoundError,
    ServiceNotFoundError,
    create_session,
)
from church_city_kids.application.get_child_attendance_history import (
    get_child_attendance_history,
)
from church_city_kids.application.get_child_details import get_child_details
from church_city_kids.application.list_children import list_children
from church_city_kids.application.list_rooms import list_rooms
from church_city_kids.application.list_service_attendances import (
    list_service_attendances,
)
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
from church_city_kids.application.update_child_guardian import (
    ChildGuardianNotFoundError,
    UpdateChildGuardianRequest,
    update_child_guardian,
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
)
from church_city_kids.domain.user import User
from church_city_kids.infrastructure.persistence.models import ServiceModel
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyAddChildGuardianRepository,
    SqlAlchemyCheckInRepository,
    SqlAlchemyCheckOutRepository,
    SqlAlchemyChildAttendanceHistoryRepository,
    SqlAlchemyCreateRoomRepository,
    SqlAlchemyCreateServiceRepository,
    SqlAlchemyCreateSessionRepository,
    SqlAlchemyGetChildDetailsRepository,
    SqlAlchemyListChildrenRepository,
    SqlAlchemyListRoomsRepository,
    SqlAlchemyMinistrySettingsRepository,
    SqlAlchemyRegistrationRepository,
    SqlAlchemyRemoveChildGuardianRepository,
    SqlAlchemyServiceAttendanceRepository,
    SqlAlchemyUpdateChildGuardianRepository,
    SqlAlchemyUserRepository,
)
from church_city_kids.infrastructure.security.jwt_tokens import JwtTokenService
from church_city_kids.infrastructure.security.passwords import PasswordHasher

app = FastAPI(
    title="Church City Kids API",
    version="0.1.0",
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


@app.post(
    "/api/services",
    response_model=CreateServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_endpoint(
    body: CreateServiceBody,
    session: Annotated[Session, Depends(get_db_session)],
    _auth: Annotated[User, Depends(require_admin)],
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
            CreateRoomRequest(name=body.name),
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
        )
        for room in result
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
