import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    http, store, sessions = client

    response = await http.post(
        "/api/v1/auth/register",
        json={"email": "newuser@test.com", "password": "strongpass"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["is_admin"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_returns_409(client):
    http, store, sessions = client

    await http.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "pass"},
    )

    response = await http.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "pass2"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_sets_cookie(client):
    http, store, sessions = client

    await http.post(
        "/api/v1/auth/register",
        json={"email": "logintest@test.com", "password": "mypassword"},
    )

    response = await http.post(
        "/api/v1/auth/login",
        json={"email": "logintest@test.com", "password": "mypassword"},
    )

    assert response.status_code == 200
    assert "session_id" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    http, store, sessions = client

    await http.post(
        "/api/v1/auth/register",
        json={"email": "wrong@test.com", "password": "correct"},
    )

    response = await http.post(
        "/api/v1/auth/login",
        json={"email": "wrong@test.com", "password": "incorrect"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    http, store, sessions = client

    response = await http.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_after_login(client):
    http, store, sessions = client

    await http.post(
        "/api/v1/auth/register",
        json={"email": "me@test.com", "password": "pass"},
    )
    await http.post(
        "/api/v1/auth/login",
        json={"email": "me@test.com", "password": "pass"},
    )

    response = await http.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"
