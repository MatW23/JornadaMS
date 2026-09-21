import pytest


@pytest.mark.anyio
async def test_client_application_is_served(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert "JornadaMS" in response.text
    assert "/static/styles.css" in response.text


@pytest.mark.anyio
async def test_client_assets_are_available(client):
    response = await client.get("/static/app.js")

    assert response.status_code == 200
    assert "auth/login" in response.text
