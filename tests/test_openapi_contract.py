"""Executable checks for the versioned API contract."""

from pathlib import Path

import yaml


def test_openapi_contract_separates_versioned_api_and_health_checks():
    contract_path = Path(__file__).parents[1] / "docs" / "api" / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    paths = contract["paths"]

    assert contract["servers"][0]["url"] == "http://localhost:8000"
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/companies" in paths
    assert "/api/v1/branches" in paths
    assert "/api/v1/time-events" in paths
    assert "/api/v1/employees/{employee_id}/activate" in paths
    assert "/api/v1/employees/{employee_id}/deactivate" in paths
    assert "/api/v1/work-schedules/{schedule_id}" in paths
    assert "/api/v1/reports/attendance" in paths
    assert "/api/v1/reports/attendance/export" in paths
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/auth/login" not in paths
    assert paths["/api/v1/time-events"]["post"]["parameters"][0]["$ref"] == (
        "#/components/parameters/IdempotencyKey"
    )
    assert contract["components"]["schemas"]["EmployeeStatus"]["enum"] == [
        "ACTIVE",
        "INACTIVE",
    ]
    assert contract["components"]["schemas"]["ScheduleStatus"]["enum"] == [
        "ACTIVE",
        "INACTIVE",
    ]
    event_type_enum = contract["components"]["schemas"]["TimeEventCreate"]["properties"][
        "event_type"
    ]["enum"]
    assert event_type_enum == [
        "ENTRADA",
        "INICIO_INTERVALO",
        "FIM_INTERVALO",
        "SAIDA",
    ]
    assert "break_start" in contract["components"]["schemas"]["WorkScheduleCreate"]["properties"]
    assert "break_end" in contract["components"]["schemas"]["WorkScheduleCreate"]["properties"]
    assert "AttendanceReportPage" in contract["components"]["schemas"]
    assert "AdjustmentRequestPage" in contract["components"]["schemas"]
    assert "SUPERSEDED" in contract["components"]["schemas"]["TimeEvent"]["properties"]["status"]["enum"]


def test_openapi_contract_has_valid_references_and_unique_operation_ids():
    contract_path = Path(__file__).parents[1] / "docs" / "api" / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    references = []

    def collect(value):
        if isinstance(value, dict):
            if "$ref" in value:
                references.append(value["$ref"])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(contract)
    missing = []
    for reference in references:
        if not reference.startswith("#/"):
            continue
        current = contract
        for part in reference[2:].split("/"):
            current = current.get(part) if isinstance(current, dict) else None
            if current is None:
                missing.append(reference)
                break

    operation_ids = [
        operation["operationId"]
        for path_item in contract["paths"].values()
        if isinstance(path_item, dict)
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert not missing
    assert len(operation_ids) == len(set(operation_ids))
