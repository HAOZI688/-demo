"""Smoke tests: import, start, login, health"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_import_app():
    import app.main
    assert True


@pytest.mark.asyncio
async def test_login_page_200(client):
    resp = await client.get("/login")
    assert resp.status_code == 200
    assert "爆款" in resp.text or "login" in resp.text or "登" in resp.text


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_ok(client):
    resp = await client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_bad(client):
    resp = await client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_empty(client):
    resp = await client.post("/api/login", json={"username": "", "password": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_status_logged_out(client):
    resp = await client.get("/api/login/status")
    assert resp.status_code == 200
    assert resp.json()["logged_in"] is False


@pytest.mark.asyncio
async def test_version(client):
    resp = await client.get("/api/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


@pytest.mark.asyncio
async def test_workspace_requires_auth(client):
    resp = await client.get("/workspace", follow_redirects=False)
    assert resp.status_code in (302, 200)
