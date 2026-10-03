from typing import Annotated

from fastapi import Depends, FastAPI, status
from sqlalchemy.orm import Session

from church_city_kids.api.dependencies import get_db_session
from church_city_kids.api.schemas import (
    CreateServiceBody,
    CreateServiceResponse,
    RegisterChildBody,
    RegisterChildResponse,
)
from church_city_kids.application.create_service import (
    CreateServiceRequest,
    create_service,
)
from church_city_kids.application.registration import (
    RegisterChildRequest,
    register_child,
)
from church_city_kids.infrastructure.persistence.repositories import (
    SqlAlchemyCreateServiceRepository,
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
