import pytest


async def _register_and_login(http, email: str, password: str = "testpass") -> None:
    """Вспомогательная функция: регистрирует и авторизует пользователя"""
    await http.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    await http.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_create_dashboard(client):
    http, store, sessions = client
    await _register_and_login(http, "creator@test.com")

    response = await http.post(
        "/api/v1/dashboards",
        json={"title": "My Dashboard"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Dashboard"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_dashboards_returns_only_own(client):
    """Каждый пользователь видит только свои дашборды (изоляция данных)"""
    http, store, sessions = client

    # Пользователь 1 создаёт дашборд
    await _register_and_login(http, "user1@test.com")
    await http.post("/api/v1/dashboards", json={"title": "User1 Dashboard"})

    # Пользователь 2 создаёт свой дашборд
    await _register_and_login(http, "user2@test.com")
    await http.post("/api/v1/dashboards", json={"title": "User2 Dashboard"})

    # Пользователь 2 видит только свой дашборд
    response = await http.get("/api/v1/dashboards")
    assert response.status_code == 200
    dashboards = response.json()
    assert len(dashboards) == 1
    assert dashboards[0]["title"] == "User2 Dashboard"


@pytest.mark.asyncio
async def test_update_dashboard(client):
    http, store, sessions = client
    await _register_and_login(http, "update@test.com")

    create_resp = await http.post("/api/v1/dashboards", json={"title": "Old Title"})
    dashboard_id = create_resp.json()["id"]

    response = await http.put(
        f"/api/v1/dashboards/{dashboard_id}",
        json={"title": "New Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_dashboard(client):
    http, store, sessions = client
    await _register_and_login(http, "delete@test.com")

    create_resp = await http.post("/api/v1/dashboards", json={"title": "To Delete"})
    dashboard_id = create_resp.json()["id"]

    delete_resp = await http.delete(f"/api/v1/dashboards/{dashboard_id}")
    assert delete_resp.status_code == 204

    # Дашборд больше недоступен
    get_resp = await http.get(f"/api/v1/dashboards/{dashboard_id}")
    assert get_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_other_user_cannot_access_dashboard(client):
    """Другой пользователь не может получить доступ к чужому дашборду"""
    http, store, sessions = client

    # Пользователь 1 создаёт дашборд
    await _register_and_login(http, "owner@test.com")
    create_resp = await http.post("/api/v1/dashboards", json={"title": "Private"})
    dashboard_id = create_resp.json()["id"]

    # Пользователь 2 пытается получить доступ
    await _register_and_login(http, "intruder@test.com")
    response = await http.get(f"/api/v1/dashboards/{dashboard_id}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_shared_dashboard_visible_to_recipient(client):
    """После шаринга получатель видит дашборд в своём списке"""
    http, store, sessions = client

    # Владелец регистрируется и создаёт дашборд
    await _register_and_login(http, "sharer@test.com")
    create_resp = await http.post("/api/v1/dashboards", json={"title": "Shared Dashboard"})
    dashboard_id = create_resp.json()["id"]

    # Получатель регистрируется, чтобы получить свой user_id
    await _register_and_login(http, "recipient@test.com")
    me_resp = await http.get("/api/v1/auth/me")
    recipient_id = me_resp.json()["id"]

    # Владелец выдаёт доступ
    await _register_and_login(http, "sharer@test.com")
    share_resp = await http.post(
        f"/api/v1/dashboards/{dashboard_id}/shares",
        json={"user_id": recipient_id, "access_level": "read"},
    )
    assert share_resp.status_code == 201

    # Получатель видит расшаренный дашборд
    await _register_and_login(http, "recipient@test.com")
    list_resp = await http.get("/api/v1/dashboards")
    titles = [d["title"] for d in list_resp.json()]
    assert "Shared Dashboard" in titles
