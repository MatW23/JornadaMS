import pytest


@pytest.mark.anyio
async def test_client_application_is_served(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert "JornadaMS" in response.text
    assert "/static/styles.css" in response.text
    assert (
        'id="attendance-actions" class="attendance-actions employee-only hidden"'
        in response.text
    )
    assert 'id="employee-attendance-nav"' in response.text
    assert 'id="reports-nav"' in response.text
    assert 'id="reports-panel"' in response.text
    assert 'id="adjustments-nav"' in response.text
    assert 'id="adjustment-form"' in response.text


@pytest.mark.anyio
async def test_client_assets_are_available(client):
    response = await client.get("/static/app.js")

    assert response.status_code == 200
    assert "auth/login" in response.text
    assert "jornada.accessToken" not in response.text
    assert "jornada.refreshToken" not in response.text
    assert "applyAppearance" in response.text
