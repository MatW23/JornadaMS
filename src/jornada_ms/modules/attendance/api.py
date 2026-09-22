"""Attendance endpoints for entrance, exit and daily history."""

# SQL statements remain complete and easy to compare with the API contract.
# ruff: noqa: E501

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import Database
from jornada_ms.modules.identity.api import get_identity_service, require_roles
from jornada_ms.modules.identity.service import IdentityService, Principal


class TimeEventCreate(BaseModel):
    event_type: str = Field(pattern="^(ENTRADA|SAIDA)$")
    occurred_at: datetime
    source: str = Field(default="WEB", pattern="^WEB$")
    employee_id: UUID | None = None


class TimeEvent(BaseModel):
    id: str
    employee_id: str
    work_date: date
    event_type: str
    occurred_at: datetime
    timezone: str
    source: str
    status: str = "VALID"


class DailySummary(BaseModel):
    work_date: date
    scheduled_minutes: int = 0
    worked_minutes: int = 0
    balance_minutes: int = 0
    delay_minutes: int = 0
    overtime_minutes: int = 0
    status: str


class TimeEventResult(BaseModel):
    event: TimeEvent
    daily_summary: DailySummary


class TimeEventPage(BaseModel):
    items: list[TimeEvent]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class DailySummaryPage(BaseModel):
    items: list[DailySummary]
    page: int
    page_size: int
    total_items: int
    total_pages: int


router = APIRouter(prefix="/api/v1", tags=["Attendance"])


def _database(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _employee_id(payload_id: UUID | None, principal: Principal) -> str:
    if payload_id is not None:
        if not set(principal.roles).intersection({"ADMIN", "HR"}):
            raise AppError(
                "FORBIDDEN", "Only administrators can register another employee", status_code=403
            )
        return str(payload_id)
    if principal.employee_id is None:
        raise AppError(
            "EMPLOYEE_REQUIRED", "Select an employee before registering attendance", status_code=422
        )
    return principal.employee_id


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise AppError("INVALID_TIMEZONE", "Employee timezone is invalid", status_code=422) from exc


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_from_row(row: Any) -> TimeEvent:
    return TimeEvent(
        id=str(row["id"]),
        employee_id=str(row["employee_id"]),
        work_date=row["work_date"],
        event_type=row["event_type"],
        occurred_at=row["occurred_at"],
        timezone=row["timezone"],
        source=row["source"],
        status="VALID",
    )


def _summary_from_row(row: Any) -> DailySummary:
    return DailySummary(
        work_date=row["work_date"],
        scheduled_minutes=int(row["scheduled_minutes"]),
        worked_minutes=int(row["worked_minutes"]),
        balance_minutes=int(row["balance_minutes"]),
        delay_minutes=int(row.get("delay_minutes", 0)),
        overtime_minutes=int(row.get("overtime_minutes", 0)),
        status=row["status"],
    )


def _calculate_worked_minutes(rows: list[Any]) -> int:
    total = 0
    opened: datetime | None = None
    for row in rows:
        occurred_at = row["occurred_at"]
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(occurred_at)
        if row["event_type"] == "ENTRADA":
            opened = occurred_at
        elif opened is not None:
            total += max(0, int((occurred_at - opened).total_seconds() // 60))
            opened = None
    return total


def _parse_datetime(value: datetime | str) -> datetime:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _schedule_metrics(
    connection: Any,
    employee_id: str,
    work_date: date,
    timezone: str,
    events: list[Any],
    worked_minutes: int,
) -> tuple[int, int, int]:
    if isinstance(work_date, str):
        work_date = date.fromisoformat(work_date)
    schedule = (
        connection.execute(
            text(
                "SELECT d.start_time, d.end_time, s.tolerance_minutes "
                "FROM employee_schedules es "
                "JOIN work_schedules s ON s.id = es.schedule_id "
                "JOIN schedule_days d ON d.schedule_id = s.id AND d.weekday = :weekday "
                "WHERE es.employee_id = :employee_id AND es.starts_on <= :work_date "
                "AND (es.ends_on IS NULL OR es.ends_on >= :work_date) "
                "AND s.status = 'ACTIVE' ORDER BY es.starts_on DESC LIMIT 1"
            ),
            {"employee_id": employee_id, "work_date": work_date, "weekday": work_date.weekday()},
        )
        .mappings()
        .first()
    )
    if schedule is None:
        return 0, 0, 0
    start = schedule["start_time"]
    end = schedule["end_time"]
    if isinstance(start, str):
        start = datetime.strptime(start, "%H:%M:%S").time()
    if isinstance(end, str):
        end = datetime.strptime(end, "%H:%M:%S").time()
    scheduled_minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if scheduled_minutes < 0:
        scheduled_minutes += 24 * 60
    local_zone = _timezone(timezone)
    first_entry = next((row for row in events if row["event_type"] == "ENTRADA"), None)
    delay_minutes = 0
    if first_entry is not None:
        occurred_at = _parse_datetime(first_entry["occurred_at"])
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=local_zone)
        local_minutes = (
            occurred_at.astimezone(local_zone).hour * 60 + occurred_at.astimezone(local_zone).minute
        )
        scheduled_start = start.hour * 60 + start.minute
        delay_minutes = max(0, local_minutes - scheduled_start - int(schedule["tolerance_minutes"]))
    return scheduled_minutes, delay_minutes, max(0, worked_minutes - scheduled_minutes)


def _upsert_summary(
    connection: Any,
    employee_id: str,
    work_date: date,
    worked_minutes: int,
    open_event: bool,
    timezone: str,
) -> DailySummary:
    if isinstance(work_date, str):
        work_date = date.fromisoformat(work_date)
    summary = (
        connection.execute(
            text(
                "SELECT work_date, scheduled_minutes, worked_minutes, overtime_minutes, delay_minutes, balance_minutes, status FROM daily_summaries WHERE employee_id = :employee_id AND work_date = :work_date"
            ),
            {"employee_id": employee_id, "work_date": work_date},
        )
        .mappings()
        .first()
    )
    summary_status = "IN_PROGRESS" if open_event else "COMPLETE"
    event_rows = (
        connection.execute(
            text(
                "SELECT event_type, occurred_at FROM time_events "
                "WHERE employee_id = :employee_id AND work_date = :work_date ORDER BY occurred_at"
            ),
            {"employee_id": employee_id, "work_date": work_date},
        )
        .mappings()
        .all()
    )
    scheduled_minutes, delay_minutes, overtime_minutes = _schedule_metrics(
        connection, employee_id, work_date, timezone, event_rows, worked_minutes
    )
    balance_minutes = worked_minutes - scheduled_minutes
    if summary is None:
        connection.execute(
            text(
                "INSERT INTO daily_summaries (id, employee_id, work_date, scheduled_minutes, worked_minutes, overtime_minutes, delay_minutes, balance_minutes, status) VALUES (:id, :employee_id, :work_date, :scheduled_minutes, :worked_minutes, :overtime_minutes, :delay_minutes, :balance_minutes, :status)"
            ),
            {
                "id": str(uuid4()),
                "employee_id": employee_id,
                "work_date": work_date,
                "scheduled_minutes": scheduled_minutes,
                "worked_minutes": worked_minutes,
                "overtime_minutes": overtime_minutes,
                "delay_minutes": delay_minutes,
                "balance_minutes": balance_minutes,
                "status": summary_status,
            },
        )
    else:
        connection.execute(
            text(
                "UPDATE daily_summaries SET scheduled_minutes = :scheduled_minutes, worked_minutes = :worked_minutes, overtime_minutes = :overtime_minutes, delay_minutes = :delay_minutes, balance_minutes = :balance_minutes, status = :status, updated_at = CURRENT_TIMESTAMP WHERE employee_id = :employee_id AND work_date = :work_date"
            ),
            {
                "employee_id": employee_id,
                "work_date": work_date,
                "scheduled_minutes": scheduled_minutes,
                "worked_minutes": worked_minutes,
                "overtime_minutes": overtime_minutes,
                "delay_minutes": delay_minutes,
                "balance_minutes": balance_minutes,
                "status": summary_status,
            },
        )
    row = (
        connection.execute(
            text(
                "SELECT work_date, scheduled_minutes, worked_minutes, overtime_minutes, delay_minutes, balance_minutes, status FROM daily_summaries WHERE employee_id = :employee_id AND work_date = :work_date"
            ),
            {"employee_id": employee_id, "work_date": work_date},
        )
        .mappings()
        .one()
    )
    return _summary_from_row(row)


@router.post(
    "/time-events",
    response_model=TimeEventResult,
    status_code=status.HTTP_201_CREATED,
    operation_id="createTimeEvent",
    responses={409: {"model": ErrorResponse}},
)
async def create_time_event(
    payload: TimeEventCreate,
    response: Response,
    principal: Principal = Depends(require_roles("ADMIN", "HR", "COLLABORATOR")),
    database: Database = Depends(_database),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
) -> TimeEventResult | JSONResponse:
    employee_id = _employee_id(payload.employee_id, principal)
    occurred_at = _as_utc(payload.occurred_at)
    try:
        with database.engine.begin() as connection:
            employee = (
                connection.execute(
                    text(
                        "SELECT e.status, b.timezone FROM employees e JOIN branches b ON b.id = e.branch_id WHERE e.id = :id"
                    ),
                    {"id": employee_id},
                )
                .mappings()
                .first()
            )
            if employee is None or employee["status"] != "ACTIVE":
                raise AppError("EMPLOYEE_NOT_FOUND", "Active employee not found", status_code=404)
            timezone = employee["timezone"]
            local_date = occurred_at.astimezone(_timezone(timezone)).date()
            if idempotency_key:
                existing = (
                    connection.execute(
                        text(
                            "SELECT id, employee_id, work_date, event_type, occurred_at, timezone, source FROM time_events WHERE employee_id = :employee_id AND idempotency_key = :idempotency_key"
                        ),
                        {"employee_id": employee_id, "idempotency_key": idempotency_key},
                    )
                    .mappings()
                    .first()
                )
                if existing is not None:
                    events = (
                        connection.execute(
                            text(
                                "SELECT event_type, occurred_at FROM time_events WHERE employee_id = :employee_id AND work_date = :work_date ORDER BY occurred_at"
                            ),
                            {"employee_id": employee_id, "work_date": existing["work_date"]},
                        )
                        .mappings()
                        .all()
                    )
                    summary = _upsert_summary(
                        connection,
                        employee_id,
                        existing["work_date"],
                        _calculate_worked_minutes(events),
                        events[-1]["event_type"] == "ENTRADA",
                        timezone,
                    )
                    return JSONResponse(
                        status_code=200,
                        content=jsonable_encoder(
                            TimeEventResult(event=_event_from_row(existing), daily_summary=summary)
                        ),
                    )
            previous = connection.execute(
                text(
                    "SELECT event_type FROM time_events WHERE employee_id = :employee_id AND work_date = :work_date ORDER BY occurred_at DESC LIMIT 1"
                ),
                {"employee_id": employee_id, "work_date": local_date},
            ).scalar_one_or_none()
            expected = "SAIDA" if previous == "ENTRADA" else "ENTRADA"
            if payload.event_type != expected:
                raise AppError(
                    "INVALID_EVENT_SEQUENCE", f"The next event must be {expected}", status_code=409
                )
            event_id = str(uuid4())
            connection.execute(
                text(
                    "INSERT INTO time_events (id, employee_id, work_date, event_type, occurred_at, timezone, source, created_by, correlation_id, idempotency_key) VALUES (:id, :employee_id, :work_date, :event_type, :occurred_at, :timezone, :source, :created_by, :correlation_id, :idempotency_key)"
                ),
                {
                    "id": event_id,
                    "employee_id": employee_id,
                    "work_date": local_date,
                    "event_type": payload.event_type,
                    "occurred_at": occurred_at,
                    "timezone": timezone,
                    "source": payload.source,
                    "created_by": principal.user_id,
                    "correlation_id": "attendance",
                    "idempotency_key": idempotency_key,
                },
            )
            events = (
                connection.execute(
                    text(
                        "SELECT event_type, occurred_at FROM time_events WHERE employee_id = :employee_id AND work_date = :work_date ORDER BY occurred_at"
                    ),
                    {"employee_id": employee_id, "work_date": local_date},
                )
                .mappings()
                .all()
            )
            summary = _upsert_summary(
                connection,
                employee_id,
                local_date,
                _calculate_worked_minutes(events),
                events[-1]["event_type"] == "ENTRADA",
                timezone,
            )
            event_row = (
                connection.execute(
                    text(
                        "SELECT id, employee_id, work_date, event_type, occurred_at, timezone, source FROM time_events WHERE id = :id"
                    ),
                    {"id": event_id},
                )
                .mappings()
                .one()
            )
    except IntegrityError as exc:
        raise AppError(
            "DUPLICATE_EVENT", "This attendance event was already registered", status_code=409
        ) from exc
    response.status_code = status.HTTP_201_CREATED
    return TimeEventResult(event=_event_from_row(event_row), daily_summary=summary)


@router.get("/time-events", response_model=TimeEventPage, operation_id="listTimeEvents")
async def list_time_events(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    employee_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    principal: Principal = Depends(require_roles("ADMIN", "HR", "COLLABORATOR")),
    database: Database = Depends(_database),
) -> TimeEventPage:
    target = _employee_id(employee_id, principal)
    if to_date < from_date:
        raise AppError(
            "INVALID_DATE_RANGE", "The end date must be after the start date", status_code=422
        )
    params = {
        "employee_id": target,
        "from_date": from_date,
        "to_date": to_date,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    with database.engine.connect() as connection:
        total = connection.execute(
            text(
                "SELECT count(*) FROM time_events WHERE employee_id = :employee_id AND work_date BETWEEN :from_date AND :to_date"
            ),
            params,
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    "SELECT id, employee_id, work_date, event_type, occurred_at, timezone, source FROM time_events WHERE employee_id = :employee_id AND work_date BETWEEN :from_date AND :to_date ORDER BY occurred_at LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
    return TimeEventPage(
        items=[_event_from_row(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/attendance/days", response_model=DailySummaryPage, operation_id="listDailySummaries")
async def list_daily_summaries(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    employee_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    principal: Principal = Depends(require_roles("ADMIN", "HR", "COLLABORATOR")),
    database: Database = Depends(_database),
) -> DailySummaryPage:
    target = _employee_id(employee_id, principal)
    params = {
        "employee_id": target,
        "from_date": from_date,
        "to_date": to_date,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    with database.engine.connect() as connection:
        total = connection.execute(
            text(
                "SELECT count(*) FROM daily_summaries WHERE employee_id = :employee_id AND work_date BETWEEN :from_date AND :to_date"
            ),
            params,
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    "SELECT work_date, scheduled_minutes, worked_minutes, overtime_minutes, delay_minutes, balance_minutes, status FROM daily_summaries WHERE employee_id = :employee_id AND work_date BETWEEN :from_date AND :to_date ORDER BY work_date DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
    return DailySummaryPage(
        items=[_summary_from_row(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )
