"""Auditable attendance adjustment requests and approval workflow."""

# SQL statements remain complete and easy to compare with the API contract.
# ruff: noqa: E501

from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette import status

from jornada_ms.api.errors import AppError, ErrorResponse
from jornada_ms.db.session import Database
from jornada_ms.modules.attendance.api import (
    _as_utc,
    _calculate_worked_minutes,
    _employee_id,
    _timezone,
    _upsert_summary,
    _validate_event_sequence,
)
from jornada_ms.modules.audit.service import record_audit
from jornada_ms.modules.identity.api import get_identity_service, require_roles
from jornada_ms.modules.identity.service import IdentityService, Principal


class AdjustmentRequestCreate(BaseModel):
    employee_id: UUID | None = None
    target_event_id: UUID | None = None
    event_type: str = Field(pattern="^(ENTRADA|INICIO_INTERVALO|FIM_INTERVALO|SAIDA)$")
    occurred_at: datetime
    reason: str = Field(min_length=10, max_length=1000)


class AdjustmentDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class AdjustmentRequest(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    work_date: str
    target_event_id: str | None
    proposed_event_type: str
    proposed_occurred_at: datetime
    proposed_timezone: str
    reason: str
    status: str
    requested_by: str
    decided_by: str | None
    decision_comment: str | None
    result_event_id: str | None
    requested_at: datetime
    decided_at: datetime | None


class AdjustmentRequestPage(BaseModel):
    items: list[AdjustmentRequest]
    page: int
    page_size: int
    total_items: int
    total_pages: int


router = APIRouter(prefix="/api/v1", tags=["Adjustments"])


def _database(service: IdentityService = Depends(get_identity_service)) -> Database:
    return service.database


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unknown")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _for_update(database: Database) -> str:
    return " FOR UPDATE" if database.engine.dialect.name == "postgresql" else ""


_REQUEST_COLUMNS = (
    "ar.id, ar.employee_id, e.name AS employee_name, ar.work_date, ar.target_event_id, "
    "ar.proposed_event_type, ar.proposed_occurred_at, ar.proposed_timezone, ar.reason, "
    "ar.status, ar.requested_by, ar.decided_by, ar.decision_comment, ar.result_event_id, "
    "ar.requested_at, ar.decided_at"
)
_REQUEST_FROM = "FROM adjustment_requests ar JOIN employees e ON e.id = ar.employee_id"


def _request(row) -> AdjustmentRequest:
    return AdjustmentRequest(
        id=str(row["id"]),
        employee_id=str(row["employee_id"]),
        employee_name=row["employee_name"],
        work_date=str(row["work_date"]),
        target_event_id=str(row["target_event_id"]) if row["target_event_id"] else None,
        proposed_event_type=row["proposed_event_type"],
        proposed_occurred_at=row["proposed_occurred_at"],
        proposed_timezone=row["proposed_timezone"],
        reason=row["reason"],
        status=row["status"],
        requested_by=str(row["requested_by"]),
        decided_by=str(row["decided_by"]) if row["decided_by"] else None,
        decision_comment=row["decision_comment"],
        result_event_id=str(row["result_event_id"]) if row["result_event_id"] else None,
        requested_at=row["requested_at"],
        decided_at=row["decided_at"],
    )


def _get_request(connection, request_id: UUID, suffix: str = ""):
    return (
        connection.execute(
            text(f"SELECT {_REQUEST_COLUMNS} {_REQUEST_FROM} WHERE ar.id = :id{suffix}"),
            {"id": str(request_id)},
        )
        .mappings()
        .first()
    )


@router.post(
    "/adjustment-requests",
    response_model=AdjustmentRequest,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAdjustmentRequest",
    responses={409: {"model": ErrorResponse}},
)
async def create_adjustment_request(
    payload: AdjustmentRequestCreate,
    request: Request,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR", "COLLABORATOR")),
) -> AdjustmentRequest:
    with database.engine.begin() as connection:
        target = None
        if payload.target_event_id is not None:
            target = (
                connection.execute(
                    text(
                        "SELECT id, employee_id, work_date, event_type, occurred_at, timezone, status "
                        f"FROM time_events WHERE id = :id{_for_update(database)}"
                    ),
                    {"id": str(payload.target_event_id)},
                )
                .mappings()
                .first()
            )
            if target is None:
                raise AppError("TIME_EVENT_NOT_FOUND", "Time event not found", status_code=404)
            if target["status"] != "VALID":
                raise AppError(
                    "TIME_EVENT_NOT_ADJUSTABLE",
                    "Only a valid time event can be adjusted",
                    status_code=409,
                )
            if "ADMIN" not in principal.roles and "HR" not in principal.roles:
                if principal.employee_id != str(target["employee_id"]):
                    raise AppError("FORBIDDEN", "The event is outside your scope", status_code=403)
            employee_id = str(target["employee_id"])
        else:
            employee_id = _employee_id(payload.employee_id, principal)

        employee = (
            connection.execute(
                text("SELECT e.status, b.timezone FROM employees e JOIN branches b ON b.id = e.branch_id WHERE e.id = :id"),
                {"id": employee_id},
            )
            .mappings()
            .first()
        )
        if employee is None or employee["status"] != "ACTIVE":
            raise AppError("EMPLOYEE_NOT_FOUND", "Active employee not found", status_code=404)
        timezone = employee["timezone"]
        proposed_at = _as_utc(payload.occurred_at)
        work_date = proposed_at.astimezone(_timezone(timezone)).date()
        target_work_date = None if target is None else target["work_date"]
        if isinstance(target_work_date, str):
            target_work_date = date.fromisoformat(target_work_date)
        if target is not None and work_date != target_work_date:
            raise AppError(
                "ADJUSTMENT_DATE_MISMATCH",
                "The proposed event must remain on the original work date",
                status_code=422,
            )
        request_id = str(uuid4())
        connection.execute(
            text(
                "INSERT INTO adjustment_requests (id, employee_id, work_date, target_event_id, proposed_event_type, proposed_occurred_at, proposed_timezone, reason, status, requested_by, correlation_id) "
                "VALUES (:id, :employee_id, :work_date, :target_event_id, :event_type, :occurred_at, :timezone, :reason, 'PENDING', :requested_by, :correlation_id)"
            ),
            {
                "id": request_id,
                "employee_id": employee_id,
                "work_date": work_date,
                "target_event_id": str(payload.target_event_id) if payload.target_event_id else None,
                "event_type": payload.event_type,
                "occurred_at": proposed_at,
                "timezone": timezone,
                "reason": payload.reason.strip(),
                "requested_by": principal.user_id,
                "correlation_id": _correlation_id(request),
            },
        )
        record_audit(
            connection,
            actor_id=principal.user_id,
            action="ADJUSTMENT_REQUESTED",
            entity_type="ADJUSTMENT_REQUEST",
            entity_id=request_id,
            result="SUCCESS",
            correlation_id=_correlation_id(request),
            ip_address=_client_ip(request),
            after_data={
                "employee_id": employee_id,
                "work_date": work_date.isoformat(),
                "target_event_id": str(payload.target_event_id) if payload.target_event_id else None,
                "event_type": payload.event_type,
                "occurred_at": proposed_at.isoformat(),
            },
        )
        row = _get_request(connection, UUID(request_id))
    return _request(row)


@router.get(
    "/adjustment-requests",
    response_model=AdjustmentRequestPage,
    operation_id="listAdjustmentRequests",
)
async def list_adjustment_requests(
    request_status: str | None = Query(
        default=None, alias="status", pattern="^(PENDING|APPROVED|REJECTED)$"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR", "COLLABORATOR")),
) -> AdjustmentRequestPage:
    is_admin = bool(set(principal.roles).intersection({"ADMIN", "HR"}))
    clauses = []
    params: dict[str, object] = {"limit": page_size, "offset": (page - 1) * page_size}
    if not is_admin:
        clauses.append("ar.employee_id = :employee_id")
        params["employee_id"] = principal.employee_id
    if request_status:
        clauses.append("ar.status = :status")
        params["status"] = request_status
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with database.engine.connect() as connection:
        total = connection.execute(
            text(f"SELECT count(*) {_REQUEST_FROM}{where}"), params
        ).scalar_one()
        rows = (
            connection.execute(
                text(
                    f"SELECT {_REQUEST_COLUMNS} {_REQUEST_FROM}{where} ORDER BY ar.requested_at DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
    return AdjustmentRequestPage(
        items=[_request(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
        total_pages=(int(total) + page_size - 1) // page_size,
    )


def _decision_comment(payload: AdjustmentDecision) -> str | None:
    return payload.comment.strip() if payload.comment else None


@router.post(
    "/adjustment-requests/{request_id}/approve",
    response_model=AdjustmentRequest,
    operation_id="approveAdjustmentRequest",
    responses={409: {"model": ErrorResponse}},
)
async def approve_adjustment_request(
    request_id: UUID,
    payload: AdjustmentDecision,
    request: Request,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> AdjustmentRequest:
    new_event_id = str(uuid4())
    with database.engine.begin() as connection:
        current = _get_request(connection, request_id, _for_update(database))
        if current is None:
            raise AppError("ADJUSTMENT_NOT_FOUND", "Adjustment request not found", status_code=404)
        if current["status"] != "PENDING":
            raise AppError("ADJUSTMENT_ALREADY_DECIDED", "Adjustment request was already decided", status_code=409)
        if str(current["requested_by"]) == principal.user_id:
            raise AppError("SELF_APPROVAL_FORBIDDEN", "The requester cannot approve their own adjustment", status_code=403)
        target = None
        if current["target_event_id"] is not None:
            target = (
                connection.execute(
                    text(
                        "SELECT id, employee_id, work_date, event_type, occurred_at, timezone, status "
                        f"FROM time_events WHERE id = :id{_for_update(database)}"
                    ),
                    {"id": str(current["target_event_id"])},
                )
                .mappings()
                .first()
            )
            if target is None or target["status"] != "VALID":
                raise AppError("TIME_EVENT_NOT_ADJUSTABLE", "The original time event is no longer valid", status_code=409)
        events = (
            connection.execute(
                text(
                    "SELECT id, event_type, occurred_at FROM time_events WHERE employee_id = :employee_id AND work_date = :work_date AND status = 'VALID'"
                ),
                {"employee_id": str(current["employee_id"]), "work_date": current["work_date"]},
            )
            .mappings()
            .all()
        )
        if target is not None:
            events = [row for row in events if str(row["id"]) != str(target["id"])]
        proposed_event = {
            "id": new_event_id,
            "event_type": current["proposed_event_type"],
            "occurred_at": current["proposed_occurred_at"],
        }
        if not _validate_event_sequence([*events, proposed_event]):
            raise AppError(
                "ADJUSTMENT_INVALID_SEQUENCE",
                "The approved event would create an invalid attendance sequence",
                status_code=409,
            )
        if target is not None:
            connection.execute(
                text("UPDATE time_events SET status = 'SUPERSEDED' WHERE id = :id"),
                {"id": str(target["id"])},
            )
        connection.execute(
            text(
                "INSERT INTO time_events (id, employee_id, work_date, event_type, occurred_at, timezone, source, status, created_by, correlation_id, idempotency_key) "
                "VALUES (:id, :employee_id, :work_date, :event_type, :occurred_at, :timezone, 'ADJUSTMENT', 'VALID', :created_by, :correlation_id, NULL)"
            ),
            {
                "id": new_event_id,
                "employee_id": str(current["employee_id"]),
                "work_date": current["work_date"],
                "event_type": current["proposed_event_type"],
                "occurred_at": current["proposed_occurred_at"],
                "timezone": current["proposed_timezone"],
                "created_by": principal.user_id,
                "correlation_id": _correlation_id(request),
            },
        )
        connection.execute(
            text(
                "UPDATE adjustment_requests SET status = 'APPROVED', decided_by = :decided_by, decision_comment = :comment, result_event_id = :result_event_id, decided_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {
                "id": str(request_id),
                "decided_by": principal.user_id,
                "comment": _decision_comment(payload),
                "result_event_id": new_event_id,
            },
        )
        valid_events = (
            connection.execute(
                text(
                    "SELECT event_type, occurred_at FROM time_events WHERE employee_id = :employee_id AND work_date = :work_date AND status = 'VALID' ORDER BY occurred_at"
                ),
                {"employee_id": str(current["employee_id"]), "work_date": current["work_date"]},
            )
            .mappings()
            .all()
        )
        _upsert_summary(
            connection,
            str(current["employee_id"]),
            current["work_date"],
            _calculate_worked_minutes(valid_events),
            valid_events[-1]["event_type"] in {"ENTRADA", "FIM_INTERVALO"},
            current["proposed_timezone"],
        )
        record_audit(
            connection,
            actor_id=principal.user_id,
            action="ADJUSTMENT_APPROVED",
            entity_type="ADJUSTMENT_REQUEST",
            entity_id=str(request_id),
            result="SUCCESS",
            correlation_id=_correlation_id(request),
            ip_address=_client_ip(request),
            after_data={"result_event_id": new_event_id, "target_event_id": current["target_event_id"]},
        )
        row = _get_request(connection, request_id)
    return _request(row)


@router.post(
    "/adjustment-requests/{request_id}/reject",
    response_model=AdjustmentRequest,
    operation_id="rejectAdjustmentRequest",
    responses={409: {"model": ErrorResponse}},
)
async def reject_adjustment_request(
    request_id: UUID,
    payload: AdjustmentDecision,
    request: Request,
    database: Database = Depends(_database),
    principal: Principal = Depends(require_roles("ADMIN", "HR")),
) -> AdjustmentRequest:
    with database.engine.begin() as connection:
        current = _get_request(connection, request_id, _for_update(database))
        if current is None:
            raise AppError("ADJUSTMENT_NOT_FOUND", "Adjustment request not found", status_code=404)
        if current["status"] != "PENDING":
            raise AppError("ADJUSTMENT_ALREADY_DECIDED", "Adjustment request was already decided", status_code=409)
        connection.execute(
            text(
                "UPDATE adjustment_requests SET status = 'REJECTED', decided_by = :decided_by, decision_comment = :comment, decided_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {
                "id": str(request_id),
                "decided_by": principal.user_id,
                "comment": _decision_comment(payload),
            },
        )
        record_audit(
            connection,
            actor_id=principal.user_id,
            action="ADJUSTMENT_REJECTED",
            entity_type="ADJUSTMENT_REQUEST",
            entity_id=str(request_id),
            result="SUCCESS",
            correlation_id=_correlation_id(request),
            ip_address=_client_ip(request),
            after_data={"comment": _decision_comment(payload)},
        )
        row = _get_request(connection, request_id)
    return _request(row)
