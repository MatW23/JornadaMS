"""Collaborator management endpoints."""

# SQL statements are kept readable as complete statements in this small module.
# ruff: noqa: E501

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import Database
from jornada_ms.modules.identity.api import get_identity_service, require_roles
from jornada_ms.modules.identity.service import IdentityService, Principal


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    registration_code: str = Field(min_length=1, max_length=64)
    branch_id: UUID
    punch_identifier: str | None = Field(default=None, max_length=64)
    department_id: UUID | None = None
    position_id: UUID | None = None
    user_id: UUID | None = None


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    registration_code: str | None = Field(default=None, min_length=1, max_length=64)
    branch_id: UUID | None = None
    punch_identifier: str | None = Field(default=None, max_length=64)
    department_id: UUID | None = None
    position_id: UUID | None = None
    user_id: UUID | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class Employee(BaseModel):
    id: str
    user_id: str | None
    company_id: str
    branch_id: str
    department_id: str | None
    position_id: str | None
    name: str
    registration_code: str
    punch_identifier: str | None
    status: str


class EmployeePage(BaseModel):
    items: list[Employee]
    page: int
    page_size: int
    total_items: int
    total_pages: int


router = APIRouter(prefix="/api/v1", tags=["Employees"])


def _db(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _employee(row) -> Employee:
    return Employee(
        **{
            key: (
                str(row[key])
                if row[key] is not None and (key.endswith("_id") or key == "id")
                else row[key]
            )
            for key in row.keys()
        }
    )


_COLUMNS = "id, user_id, company_id, branch_id, department_id, position_id, name, registration_code, punch_identifier, status"


@router.get("/employees", response_model=EmployeePage, operation_id="listEmployees")
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=160),
    database: Database = Depends(_db),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> EmployeePage:
    del principal
    where = (
        " WHERE lower(name) LIKE :search OR lower(registration_code) LIKE :search" if search else ""
    )
    params = {
        "search": f"%{search.casefold()}%" if search else None,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    with database.engine.connect() as connection:
        total = connection.execute(
            text(f"SELECT count(*) FROM employees{where}"), params
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    f"SELECT {_COLUMNS} FROM employees{where} ORDER BY name LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
    return EmployeePage(
        items=[_employee(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/employees",
    response_model=Employee,
    status_code=status.HTTP_201_CREATED,
    operation_id="createEmployee",
    responses={409: {"model": ErrorResponse}},
)
async def create_employee(
    payload: EmployeeCreate,
    database: Database = Depends(_db),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Employee:
    del principal
    employee_id = str(uuid4())
    try:
        with database.engine.begin() as connection:
            branch = connection.execute(
                text("SELECT company_id FROM branches WHERE id = :id AND status = 'ACTIVE'"),
                {"id": str(payload.branch_id)},
            ).scalar_one_or_none()
            if branch is None:
                raise AppError("BRANCH_NOT_FOUND", "Active branch not found", status_code=404)
            values = {
                "id": employee_id,
                "company_id": str(branch),
                "branch_id": str(payload.branch_id),
                "name": payload.name.strip(),
                "registration_code": payload.registration_code.strip(),
                "punch_identifier": payload.punch_identifier,
                "department_id": str(payload.department_id) if payload.department_id else None,
                "position_id": str(payload.position_id) if payload.position_id else None,
                "user_id": str(payload.user_id) if payload.user_id else None,
            }
            connection.execute(
                text(
                    "INSERT INTO employees (id, company_id, branch_id, name, registration_code, punch_identifier, department_id, position_id, user_id) VALUES (:id, :company_id, :branch_id, :name, :registration_code, :punch_identifier, :department_id, :position_id, :user_id)"
                ),
                values,
            )
            row = (
                connection.execute(
                    text(f"SELECT {_COLUMNS} FROM employees WHERE id = :id"), {"id": employee_id}
                )
                .mappings()
                .one()
            )
    except IntegrityError as exc:
        raise AppError(
            "EMPLOYEE_ALREADY_EXISTS",
            "Registration code or linked user already exists",
            status_code=409,
        ) from exc
    return _employee(row)


@router.get("/employees/{employee_id}", response_model=Employee, operation_id="getEmployee")
async def get_employee(
    employee_id: UUID,
    database: Database = Depends(_db),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Employee:
    del principal
    with database.engine.connect() as connection:
        row = (
            connection.execute(
                text(f"SELECT {_COLUMNS} FROM employees WHERE id = :id"), {"id": str(employee_id)}
            )
            .mappings()
            .first()
        )
    if row is None:
        raise AppError("EMPLOYEE_NOT_FOUND", "Employee not found", status_code=404)
    return _employee(row)


@router.patch(
    "/employees/{employee_id}",
    response_model=Employee,
    operation_id="updateEmployee",
    responses={409: {"model": ErrorResponse}},
)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    database: Database = Depends(_db),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Employee:
    del principal
    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields:
        fields["name"] = fields["name"].strip()
    for key in ("branch_id", "department_id", "position_id", "user_id"):
        if key in fields and fields[key] is not None:
            fields[key] = str(fields[key])
    if not fields:
        with database.engine.connect() as connection:
            row = (
                connection.execute(
                    text(f"SELECT {_COLUMNS} FROM employees WHERE id = :id"),
                    {"id": str(employee_id)},
                )
                .mappings()
                .first()
            )
        if row is None:
            raise AppError("EMPLOYEE_NOT_FOUND", "Employee not found", status_code=404)
        return _employee(row)
    fields["id"] = str(employee_id)
    assignments = ", ".join(f"{key} = :{key}" for key in fields if key != "id")
    try:
        with database.engine.begin() as connection:
            if "branch_id" in fields:
                company_id = connection.execute(
                    text(
                        "SELECT company_id FROM branches WHERE id = :branch_id AND status = 'ACTIVE'"
                    ),
                    fields,
                ).scalar_one_or_none()
                if company_id is None:
                    raise AppError("BRANCH_NOT_FOUND", "Active branch not found", status_code=404)
                fields["company_id"] = str(company_id)
                assignments += ", company_id = :company_id"
            connection.execute(
                text(
                    f"UPDATE employees SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                fields,
            )
            row = (
                connection.execute(text(f"SELECT {_COLUMNS} FROM employees WHERE id = :id"), fields)
                .mappings()
                .first()
            )
    except IntegrityError as exc:
        raise AppError(
            "EMPLOYEE_ALREADY_EXISTS",
            "Registration code or linked user already exists",
            status_code=409,
        ) from exc
    if row is None:
        raise AppError("EMPLOYEE_NOT_FOUND", "Employee not found", status_code=404)
    return _employee(row)
