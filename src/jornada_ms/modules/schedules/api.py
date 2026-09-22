"""Simple work schedule management for MVP-1."""

# SQL statements remain complete and easy to compare with the API contract.
# ruff: noqa: E501

from datetime import date, time
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


class WorkScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    start_time: time
    end_time: time
    same_day_only: bool = True
    tolerance_minutes: int = Field(default=0, ge=0, le=240)


class WorkScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    start_time: time | None = None
    end_time: time | None = None
    same_day_only: bool | None = None
    tolerance_minutes: int | None = Field(default=None, ge=0, le=240)


class WorkSchedule(BaseModel):
    id: str
    name: str
    start_time: time
    end_time: time
    same_day_only: bool
    tolerance_minutes: int
    status: str


class WorkSchedulePage(BaseModel):
    items: list[WorkSchedule]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class EmployeeScheduleCreate(BaseModel):
    schedule_id: UUID
    starts_on: date
    ends_on: date | None = None


class EmployeeSchedule(EmployeeScheduleCreate):
    employee_id: str


router = APIRouter(prefix="/api/v1", tags=["Schedules"])


def _database(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _schedule(row) -> WorkSchedule:
    return WorkSchedule(
        id=str(row["id"]),
        name=row["name"],
        start_time=row["start_time"],
        end_time=row["end_time"],
        same_day_only=row["same_day_only"],
        tolerance_minutes=row["tolerance_minutes"],
        status=row["status"],
    )


def _time_value(value: time | str) -> time:
    return time.fromisoformat(value) if isinstance(value, str) else value


_SCHEDULE_COLUMNS = (
    "s.id, s.name, d.start_time, d.end_time, s.same_day_only, s.tolerance_minutes, s.status"
)
_SCHEDULE_QUERY = f"SELECT {_SCHEDULE_COLUMNS} FROM work_schedules s JOIN schedule_days d ON d.schedule_id = s.id AND d.weekday = 0"


@router.get("/work-schedules", response_model=WorkSchedulePage, operation_id="listWorkSchedules")
async def list_work_schedules(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    schedule_status: str | None = Query(
        default=None, alias="status", pattern="^(ACTIVE|INACTIVE)$"
    ),
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> WorkSchedulePage:
    del principal
    where = " WHERE s.status = :status" if schedule_status else ""
    params = {"status": schedule_status, "limit": page_size, "offset": (page - 1) * page_size}
    with database.engine.connect() as connection:
        total = connection.execute(
            text(f"SELECT count(*) FROM work_schedules s{where}"), params
        ).scalar_one()
        rows = (
            connection.execute(
                text(f"{_SCHEDULE_QUERY}{where} ORDER BY s.name LIMIT :limit OFFSET :offset"),
                params,
            )
            .mappings()
            .all()
        )
    return WorkSchedulePage(
        items=[_schedule(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/work-schedules",
    response_model=WorkSchedule,
    status_code=status.HTTP_201_CREATED,
    operation_id="createWorkSchedule",
)
async def create_work_schedule(
    payload: WorkScheduleCreate,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> WorkSchedule:
    del principal
    if payload.end_time <= payload.start_time and payload.same_day_only:
        raise AppError("INVALID_SCHEDULE", "End time must be after start time", status_code=422)
    schedule_id = str(uuid4())
    with database.engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO work_schedules (id, name, tolerance_minutes, same_day_only) VALUES (:id, :name, :tolerance, :same_day)"
            ),
            {
                "id": schedule_id,
                "name": payload.name.strip(),
                "tolerance": payload.tolerance_minutes,
                "same_day": payload.same_day_only,
            },
        )
        for weekday in range(5):
            connection.execute(
                text(
                    "INSERT INTO schedule_days (id, schedule_id, weekday, start_time, end_time) VALUES (:id, :schedule_id, :weekday, :start_time, :end_time)"
                ),
                {
                    "id": str(uuid4()),
                    "schedule_id": schedule_id,
                    "weekday": weekday,
                    "start_time": payload.start_time.isoformat(),
                    "end_time": payload.end_time.isoformat(),
                },
            )
        row = (
            connection.execute(text(f"{_SCHEDULE_QUERY} WHERE s.id = :id"), {"id": schedule_id})
            .mappings()
            .one()
        )
    return _schedule(row)


@router.get(
    "/work-schedules/{schedule_id}", response_model=WorkSchedule, operation_id="getWorkSchedule"
)
async def get_work_schedule(
    schedule_id: UUID,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> WorkSchedule:
    del principal
    with database.engine.connect() as connection:
        row = (
            connection.execute(
                text(f"{_SCHEDULE_QUERY} WHERE s.id = :id"), {"id": str(schedule_id)}
            )
            .mappings()
            .first()
        )
    if row is None:
        raise AppError("SCHEDULE_NOT_FOUND", "Work schedule not found", status_code=404)
    return _schedule(row)


@router.patch(
    "/work-schedules/{schedule_id}", response_model=WorkSchedule, operation_id="updateWorkSchedule"
)
async def update_work_schedule(
    schedule_id: UUID,
    payload: WorkScheduleUpdate,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> WorkSchedule:
    del principal
    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields:
        fields["name"] = fields["name"].strip()
    with database.engine.begin() as connection:
        existing = (
            connection.execute(
                text(f"{_SCHEDULE_QUERY} WHERE s.id = :id"), {"id": str(schedule_id)}
            )
            .mappings()
            .first()
        )
        if existing is None:
            raise AppError("SCHEDULE_NOT_FOUND", "Work schedule not found", status_code=404)
        start_time = _time_value(fields.get("start_time", existing["start_time"]))
        end_time = _time_value(fields.get("end_time", existing["end_time"]))
        same_day = fields.get("same_day_only", existing["same_day_only"])
        if same_day and end_time <= start_time:
            raise AppError("INVALID_SCHEDULE", "End time must be after start time", status_code=422)
        schedule_fields = {
            key: value
            for key, value in fields.items()
            if key in {"name", "same_day_only", "tolerance_minutes"}
        }
        if schedule_fields:
            assignments = ", ".join(f"{key} = :{key}" for key in schedule_fields)
            schedule_fields["id"] = str(schedule_id)
            connection.execute(
                text(
                    f"UPDATE work_schedules SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                schedule_fields,
            )
            connection.execute(
                text(
                    "UPDATE schedule_days SET start_time = :start_time, end_time = :end_time WHERE schedule_id = :id"
                ),
                {
                    "id": str(schedule_id),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )
        row = (
            connection.execute(
                text(f"{_SCHEDULE_QUERY} WHERE s.id = :id"), {"id": str(schedule_id)}
            )
            .mappings()
            .one()
        )
    return _schedule(row)


@router.post(
    "/employees/{employee_id}/schedules",
    response_model=EmployeeSchedule,
    status_code=status.HTTP_201_CREATED,
    operation_id="assignEmployeeSchedule",
    responses={409: {"model": ErrorResponse}},
)
async def assign_employee_schedule(
    employee_id: UUID,
    payload: EmployeeScheduleCreate,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> EmployeeSchedule:
    del principal
    if payload.ends_on is not None and payload.ends_on < payload.starts_on:
        raise AppError(
            "INVALID_DATE_RANGE", "Schedule end date must be after start date", status_code=422
        )
    try:
        with database.engine.begin() as connection:
            employee = connection.execute(
                text("SELECT id FROM employees WHERE id = :id AND status = 'ACTIVE'"),
                {"id": str(employee_id)},
            ).first()
            schedule = connection.execute(
                text("SELECT id FROM work_schedules WHERE id = :id AND status = 'ACTIVE'"),
                {"id": str(payload.schedule_id)},
            ).first()
            if employee is None:
                raise AppError("EMPLOYEE_NOT_FOUND", "Active employee not found", status_code=404)
            if schedule is None:
                raise AppError(
                    "SCHEDULE_NOT_FOUND", "Active work schedule not found", status_code=404
                )
            connection.execute(
                text(
                    "INSERT INTO employee_schedules (employee_id, schedule_id, starts_on, ends_on) VALUES (:employee_id, :schedule_id, :starts_on, :ends_on)"
                ),
                {
                    "employee_id": str(employee_id),
                    "schedule_id": str(payload.schedule_id),
                    "starts_on": payload.starts_on,
                    "ends_on": payload.ends_on,
                },
            )
    except IntegrityError as exc:
        raise AppError(
            "SCHEDULE_ALREADY_ASSIGNED",
            "This schedule is already assigned to the employee",
            status_code=409,
        ) from exc
    return EmployeeSchedule(employee_id=str(employee_id), **payload.model_dump())
