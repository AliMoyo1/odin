import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.models.models import TaskChangelog
from tests.conftest import TEST_EMAIL, TEST_PASSWORD, _TASKS_XFF


@pytest.fixture
async def ac(test_user):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Forwarded-For": _TASKS_XFF},
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


async def test_create_task(ac):
    resp = await ac.post("/api/v1/tasks", json={"title": "My first task"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My first task"
    assert data["status"] == "backlog"
    assert data["priority"] == "medium"


async def test_update_status_produces_one_changelog_row(ac, test_user):
    create = await ac.post("/api/v1/tasks", json={"title": "Changelog test"})
    assert create.status_code == 201
    task_id = create.json()["id"]

    patch = await ac.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
    assert patch.status_code == 200
    assert patch.json()["status"] == "in_progress"

    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        result = await s.execute(
            select(TaskChangelog).where(
                TaskChangelog.task_id == task_id,
                TaskChangelog.field_name == "status",
            )
        )
        rows = result.scalars().all()
    await engine.dispose()

    assert len(rows) == 1
    assert rows[0].old_value == "backlog"
    assert rows[0].new_value == "in_progress"


async def test_update_no_change_produces_zero_changelog_rows(ac, test_user):
    create = await ac.post("/api/v1/tasks", json={"title": "No-op test", "status": "todo"})
    assert create.status_code == 201
    task_id = create.json()["id"]

    patch = await ac.patch(f"/api/v1/tasks/{task_id}", json={"status": "todo"})
    assert patch.status_code == 200

    engine = create_async_engine(settings.DATABASE_URL)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        result = await s.execute(
            select(TaskChangelog).where(TaskChangelog.task_id == task_id)
        )
        rows = result.scalars().all()
    await engine.dispose()

    assert len(rows) == 0


async def test_pagination_limit_caps_at_200(ac):
    resp = await ac.get("/api/v1/tasks?limit=999")
    assert resp.status_code == 422


async def test_subtask_toggle(ac):
    task = await ac.post("/api/v1/tasks", json={"title": "Parent task"})
    assert task.status_code == 201
    task_id = task.json()["id"]

    sub = await ac.post(f"/api/v1/tasks/{task_id}/subtasks", json={"title": "Do the thing"})
    assert sub.status_code == 201
    sub_id = sub.json()["id"]
    assert sub.json()["done"] is False

    toggled = await ac.patch(f"/api/v1/subtasks/{sub_id}", json={"done": True})
    assert toggled.status_code == 200
    assert toggled.json()["done"] is True

    reset = await ac.patch(f"/api/v1/subtasks/{sub_id}", json={"done": False})
    assert reset.status_code == 200
    assert reset.json()["done"] is False
