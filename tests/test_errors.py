from jornada_ms.api.errors import sanitize_validation_errors


def test_validation_details_do_not_echo_submitted_values() -> None:
    details = sanitize_validation_errors(
        [
            {
                "loc": ("body", "password"),
                "type": "string_type",
                "msg": "Input should be a valid string",
                "input": "super-secret-token",
                "ctx": {"hint": "private"},
            }
        ]
    )

    assert details == [{"loc": ["body", "password"], "type": "string_type"}]
