"""Organization setup endpoints used by the first client workflow."""

# SQL statements are kept readable as complete statements in this small module.
# ruff: noqa: E501

from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import Database
from jornada_ms.modules.audit.service import record_audit
from jornada_ms.modules.identity.api import get_identity_service, require_roles
from jornada_ms.modules.identity.service import IdentityService, Principal


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    cnpj: str = Field(pattern=r"^\d{14}$")
    default_timezone: str = Field(min_length=1, max_length=64)

    @field_validator("default_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone") from exc
        return value


class Company(BaseModel):
    id: str
    name: str
    cnpj: str
    default_timezone: str
    status: str


class BranchCreate(BaseModel):
    company_id: str
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=40)
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone") from exc
        return value


class Branch(BaseModel):
    id: str
    company_id: str
    name: str
    code: str
    timezone: str
    status: str


class Page(BaseModel):
    items: list
    page: int
    page_size: int
    total_items: int
    total_pages: int


router = APIRouter(prefix="/api/v1", tags=["Organization"])


def _service_database(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/companies", response_model=Page, operation_id="listCompanies")
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    database: Database = Depends(_service_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Page:
    del principal
    with database.engine.connect() as connection:
        total = connection.execute(text("SELECT count(*) FROM companies")).scalar_one()
        rows = (
            connection.execute(
                text(
                    "SELECT id, name, cnpj, default_timezone, status FROM companies ORDER BY name LIMIT :limit OFFSET :offset"
                ),
                {"limit": page_size, "offset": (page - 1) * page_size},
            )
            .mappings()
            .all()
        )
    return Page(
        items=[Company(**dict(row)) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/companies",
    response_model=Company,
    status_code=status.HTTP_201_CREATED,
    operation_id="createCompany",
    responses={409: {"model": ErrorResponse}},
)
async def create_company(
    payload: CompanyCreate,
    request: Request,
    database: Database = Depends(_service_database),
    principal: Principal = Depends(require_roles("ADMIN")),
) -> Company:
    company_id = str(uuid4())
    try:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO companies (id, name, cnpj, default_timezone) VALUES (:id, :name, :cnpj, :timezone)"
                ),
                {
                    "id": company_id,
                    "name": payload.name.strip(),
                    "cnpj": payload.cnpj,
                    "timezone": payload.default_timezone,
                },
            )
            record_audit(
                connection,
                actor_id=principal.user_id,
                action="COMPANY_CREATED",
                entity_type="COMPANY",
                entity_id=company_id,
                result="SUCCESS",
                correlation_id=_correlation_id(request),
                ip_address=_client_ip(request),
                after_data={
                    "name": payload.name.strip(),
                    "cnpj": payload.cnpj,
                    "default_timezone": payload.default_timezone,
                },
            )
    except IntegrityError as exc:
        raise AppError(
            "COMPANY_ALREADY_EXISTS", "A company with this CNPJ already exists", status_code=409
        ) from exc
    return Company(
        id=company_id,
        name=payload.name.strip(),
        cnpj=payload.cnpj,
        default_timezone=payload.default_timezone,
        status="ACTIVE",
    )


@router.get("/branches", response_model=Page, operation_id="listBranches")
async def list_branches(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    company_id: str | None = None,
    database: Database = Depends(_service_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Page:
    del principal
    where = " WHERE company_id = :company_id" if company_id else ""
    params = {"company_id": company_id, "limit": page_size, "offset": (page - 1) * page_size}
    with database.engine.connect() as connection:
        total = connection.execute(
            text(f"SELECT count(*) FROM branches{where}"), params
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    f"SELECT id, company_id, name, code, timezone, status FROM branches{where} ORDER BY name LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
    return Page(
        items=[Branch(**dict(row)) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/branches",
    response_model=Branch,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBranch",
    responses={409: {"model": ErrorResponse}},
)
async def create_branch(
    payload: BranchCreate,
    request: Request,
    database: Database = Depends(_service_database),
    principal: Principal = Depends(require_roles("ADMIN")),
) -> Branch:
    branch_id = str(uuid4())
    try:
        with database.engine.begin() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM companies WHERE id = :id"), {"id": payload.company_id}
            ).first()
            if not exists:
                raise AppError("COMPANY_NOT_FOUND", "Company not found", status_code=404)
            connection.execute(
                text(
                    "INSERT INTO branches (id, company_id, name, code, timezone) VALUES (:id, :company_id, :name, :code, :timezone)"
                ),
                {
                    "id": branch_id,
                    "company_id": payload.company_id,
                    "name": payload.name.strip(),
                    "code": payload.code.strip(),
                    "timezone": payload.timezone,
                },
            )
            record_audit(
                connection,
                actor_id=principal.user_id,
                action="BRANCH_CREATED",
                entity_type="BRANCH",
                entity_id=branch_id,
                result="SUCCESS",
                correlation_id=_correlation_id(request),
                ip_address=_client_ip(request),
                after_data={
                    "company_id": payload.company_id,
                    "name": payload.name.strip(),
                    "code": payload.code.strip(),
                    "timezone": payload.timezone,
                },
            )
    except IntegrityError as exc:
        raise AppError(
            "BRANCH_ALREADY_EXISTS", "A branch with this code already exists", status_code=409
        ) from exc
    return Branch(
        id=branch_id,
        company_id=payload.company_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        timezone=payload.timezone,
        status="ACTIVE",
    )
