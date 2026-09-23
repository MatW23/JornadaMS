"""Operational attendance reports built from authoritative daily summaries."""

# SQL statements remain complete and easy to compare with the API contract.
# ruff: noqa: E501

import csv
from datetime import date
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import Database
from jornada_ms.modules.audit.service import record_audit
from jornada_ms.modules.identity.api import get_identity_service, require_roles
from jornada_ms.modules.identity.service import IdentityService, Principal


class AttendanceReportItem(BaseModel):
    employee_id: str
    employee_name: str
    registration_code: str
    work_date: date
    scheduled_minutes: int
    worked_minutes: int
    balance_minutes: int
    delay_minutes: int
    overtime_minutes: int
    status: str


class AttendanceReportTotals(BaseModel):
    scheduled_minutes: int = 0
    worked_minutes: int = 0
    balance_minutes: int = 0
    delay_minutes: int = 0
    overtime_minutes: int = 0


class AttendanceReportPage(BaseModel):
    items: list[AttendanceReportItem]
    from_date: date
    to_date: date
    page: int
    page_size: int
    total_items: int
    total_pages: int
    totals: AttendanceReportTotals


router = APIRouter(prefix="/api/v1", tags=["Reporting"])


def _database(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _validate_period(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise AppError(
            "INVALID_DATE_RANGE", "The end date must be after the start date", status_code=422
        )
    if (to_date - from_date).days > 366:
        raise AppError(
            "REPORT_RANGE_TOO_LARGE",
            "The report period cannot exceed 366 days",
            status_code=422,
        )


def _filters(
    from_date: date,
    to_date: date,
    employee_id: UUID | None,
    report_status: str | None,
) -> tuple[str, dict]:
    clauses = ["ds.work_date BETWEEN :from_date AND :to_date"]
    params: dict[str, object] = {"from_date": from_date, "to_date": to_date}
    if employee_id is not None:
        clauses.append("ds.employee_id = :employee_id")
        params["employee_id"] = str(employee_id)
    if report_status is not None:
        clauses.append("ds.status = :report_status")
        params["report_status"] = report_status
    return " AND ".join(clauses), params


def _item(row) -> AttendanceReportItem:
    return AttendanceReportItem(
        employee_id=str(row["employee_id"]),
        employee_name=row["employee_name"],
        registration_code=row["registration_code"],
        work_date=row["work_date"],
        scheduled_minutes=int(row["scheduled_minutes"]),
        worked_minutes=int(row["worked_minutes"]),
        balance_minutes=int(row["balance_minutes"]),
        delay_minutes=int(row["delay_minutes"]),
        overtime_minutes=int(row["overtime_minutes"]),
        status=row["status"],
    )


_REPORT_FROM = (
    "FROM daily_summaries ds "
    "JOIN employees e ON e.id = ds.employee_id"
)
_REPORT_COLUMNS = (
    "ds.employee_id, e.name AS employee_name, e.registration_code, ds.work_date, "
    "ds.scheduled_minutes, ds.worked_minutes, ds.balance_minutes, ds.delay_minutes, "
    "ds.overtime_minutes, ds.status"
)


def _query_report(
    database: Database,
    from_date: date,
    to_date: date,
    employee_id: UUID | None,
    report_status: str | None,
    page: int | None,
    page_size: int | None,
) -> tuple[list[AttendanceReportItem], int, AttendanceReportTotals]:
    where, params = _filters(from_date, to_date, employee_id, report_status)
    with database.engine.connect() as connection:
        total = connection.execute(
            text(f"SELECT count(*) {_REPORT_FROM} WHERE {where}"), params
        ).scalar_one()
        totals_row = (
            connection.execute(
                text(
                    "SELECT "
                    "COALESCE(sum(ds.scheduled_minutes), 0) AS scheduled_minutes, "
                    "COALESCE(sum(ds.worked_minutes), 0) AS worked_minutes, "
                    "COALESCE(sum(ds.balance_minutes), 0) AS balance_minutes, "
                    "COALESCE(sum(ds.delay_minutes), 0) AS delay_minutes, "
                    "COALESCE(sum(ds.overtime_minutes), 0) AS overtime_minutes "
                    f"{_REPORT_FROM} WHERE {where}"
                ),
                params,
            )
            .mappings()
            .one()
        )
        query = f"SELECT {_REPORT_COLUMNS} {_REPORT_FROM} WHERE {where} ORDER BY ds.work_date DESC, e.name"
        if page is not None and page_size is not None:
            query += " LIMIT :limit OFFSET :offset"
            params = {**params, "limit": page_size, "offset": (page - 1) * page_size}
        rows = connection.execute(text(query), params).mappings().all()
    return (
        [_item(row) for row in rows],
        int(total),
        AttendanceReportTotals(**dict(totals_row)),
    )


@router.get(
    "/reports/attendance",
    response_model=AttendanceReportPage,
    operation_id="getAttendanceReport",
    responses={422: {"model": ErrorResponse}},
)
async def get_attendance_report(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    employee_id: UUID | None = None,
    report_status: str | None = Query(
        default=None, alias="status", pattern="^(IN_PROGRESS|COMPLETE|INCONSISTENT)$"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> AttendanceReportPage:
    del principal
    _validate_period(from_date, to_date)
    items, total, totals = _query_report(
        database, from_date, to_date, employee_id, report_status, page, page_size
    )
    return AttendanceReportPage(
        items=items,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
        totals=totals,
    )


@router.get(
    "/reports/attendance/export",
    operation_id="exportAttendanceReport",
    responses={
        200: {"content": {"text/csv": {"schema": {"type": "string"}}}},
        422: {"model": ErrorResponse},
    },
)
async def export_attendance_report(
    request: Request,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    employee_id: UUID | None = None,
    report_status: str | None = Query(
        default=None, alias="status", pattern="^(IN_PROGRESS|COMPLETE|INCONSISTENT)$"
    ),
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> Response:
    _validate_period(from_date, to_date)
    items, _total, _totals = _query_report(
        database, from_date, to_date, employee_id, report_status, None, None
    )
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(
        [
            "employee_id",
            "employee_name",
            "registration_code",
            "work_date",
            "scheduled_minutes",
            "worked_minutes",
            "balance_minutes",
            "delay_minutes",
            "overtime_minutes",
            "status",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.employee_id,
                item.employee_name,
                item.registration_code,
                item.work_date.isoformat(),
                item.scheduled_minutes,
                item.worked_minutes,
                item.balance_minutes,
                item.delay_minutes,
                item.overtime_minutes,
                item.status,
            ]
        )
    with database.engine.begin() as connection:
        record_audit(
            connection,
            actor_id=principal.user_id,
            action="ATTENDANCE_REPORT_EXPORTED",
            entity_type="ATTENDANCE_REPORT",
            entity_id=None,
            result="SUCCESS",
            correlation_id=_correlation_id(request),
            ip_address=_client_ip(request),
            after_data={
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "employee_id": str(employee_id) if employee_id else None,
                "status": report_status,
                "format": "csv",
                "row_count": len(items),
            },
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="jornada-relatorio.csv"'},
    )
