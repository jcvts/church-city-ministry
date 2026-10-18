from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import get_db_session
from church_city_kids.api.schemas import (
    CheckInBody,
    CheckInResponse,
    CheckOutBody,
    CheckOutResponse,
    CreateRoomBody,
    CreateRoomResponse,
    CreateServiceBody,
    CreateServiceResponse,
    CreateSessionBody,
    CreateSessionResponse,
    RegisterChildBody,
    RegisterChildResponse,
    RoomResponse,
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
    create_service,
)
from church_city_kids.application.create_session import (
    CreateSessionRequest,
    RoomNotFoundError,
    ServiceNotFoundError,
    create_session,
)
from church_city_kids.application.list_rooms import list_rooms
from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.domain.errors import (
    AttendanceAlreadyCheckedOutError,
    CheckOutBeforeCheckInError,
    ChildAgeOutOfRangeError,
    ChildAlreadyCheckedInError,
    ChildInactiveError,
    FamilyInactiveError,
    GuardianNotAuthorizedForPickupError,
    InvalidAgeRangeError,
    RoomAlreadyAssignedInServiceError,
    RoomInactiveError,
    RoomNameAlreadyExistsError,
    SessionNotOpenError,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyCheckInRepository,
    SqlAlchemyCheckOutRepository,
    SqlAlchemyCreateRoomRepository,
    SqlAlchemyCreateServiceRepository,
    SqlAlchemyCreateSessionRepository,
    SqlAlchemyListRoomsRepository,
    SqlAlchemyRegistrationRepository,
)

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


@app.post(
    "/api/services",
    response_model=CreateServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service_endpoint(
    body: CreateServiceBody,
    session: Annotated[Session, Depends(get_db_session)],
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


@app.post(
    "/api/rooms",
    response_model=CreateRoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room_endpoint(
    body: CreateRoomBody,
    session: Annotated[Session, Depends(get_db_session)],
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
