import sqlite3

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as client:
        yield client


def test_crud_and_persistence(client):
    response = client.post("/api/tasks", json={"title": "  Regression  "})
    assert response.status_code == 201
    task = response.json()
    assert task == {"id": task["id"], "title": "Regression", "done": False}
    assert client.patch(f"/api/tasks/{task['id']}", json={"done": True}).json()["done"] is True
    assert client.get("/api/tasks").json() == [{**task, "done": True}]
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get("/api/tasks").json() == []

@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 121}, {"title": None}, {"title": 123}])
def test_invalid_titles_do_not_write(client, payload):
    assert client.post("/api/tasks", json=payload).status_code == 422
    assert client.get("/api/tasks").json() == []

@pytest.mark.parametrize("title", ["x", "x" * 120, "Проверка 中文", "Robert'); DROP TABLE tasks;--"])
def test_valid_boundaries_and_sql_safety(client, title):
    assert client.post("/api/tasks", json={"title": title}).json()["title"] == title
    assert len(client.get("/api/tasks").json()) == 1

@pytest.mark.parametrize("method,payload", [("patch", {"done": True}), ("delete", None)])
def test_missing_task(client, method, payload):
    assert client.request(method, "/api/tasks/999", **({"json": payload} if payload else {})).status_code == 404

@pytest.mark.parametrize("done", ["false", 1, None])
def test_strict_boolean(client, done):
    task = client.post("/api/tasks", json={"title": "Check"}).json()
    assert client.patch(f"/api/tasks/{task['id']}", json={"done": done}).status_code == 422
    assert client.get("/api/tasks").json()[0]["done"] is False

def test_database_matches_api(client, monkeypatch):
    import os
    task = client.post("/api/tasks", json={"title": "SQL validation"}).json()
    with sqlite3.connect(os.environ["DB_PATH"]) as db:
        assert db.execute("SELECT title, done FROM tasks WHERE id = ?", (task["id"],)).fetchone() == ("SQL validation", 0)

def test_metrics_use_route_templates(client):
    client.get("/health")
    client.delete("/api/tasks/999")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'route="/api/tasks/{task_id}"' in response.text
    assert 'qa_http_duration_seconds_bucket' in response.text
