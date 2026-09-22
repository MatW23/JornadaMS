"""Shared persistence helper for security and business audit events."""

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text


def record_audit(
    connection: Any,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    result: str,
    correlation_id: str,
    ip_address: str | None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
) -> None:
    """Write a structured audit event in the caller's transaction."""

    connection.execute(
        text(
            "INSERT INTO audit_events "
            "(id, actor_id, action, entity_type, entity_id, before_data, after_data, result, "
            "correlation_id, ip_address) "
            "VALUES (:id, :actor_id, :action, :entity_type, :entity_id, :before_data, "
            ":after_data, :result, :correlation_id, :ip_address)"
        ),
        {
            "id": str(uuid4()),
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "before_data": (
                json.dumps(before_data, default=str) if before_data is not None else None
            ),
            "after_data": (
                json.dumps(after_data, default=str) if after_data is not None else None
            ),
            "result": result,
            "correlation_id": correlation_id,
            "ip_address": ip_address,
        },
    )
