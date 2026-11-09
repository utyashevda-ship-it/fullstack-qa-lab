import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest

app = FastAPI(title="QA Task Lab", version="1.0.0")
REQUESTS = Counter("qa_http_requests_total", "HTTP responses", ["method", "route", "status"])
LATENCY = Histogram("qa_http_duration_seconds", "HTTP duration", ["method", "route"])

@contextmanager
def database():
    connection = sqlite3.connect(os.getenv("DB_PATH", "tasks.db"))
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)")
        yield connection
        connection.commit()
    finally:
        connection.close()

@app.middleware("http")
async def metrics(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    label = route.path if route else "unmatched"
    if label != "/metrics":
        REQUESTS.labels(request.method, label, str(response.status_code)).inc()
        LATENCY.labels(request.method, label).observe(time.perf_counter() - start)
    return response

class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Title must not be blank")
        return value

class TaskUpdate(BaseModel):
    done: bool = Field(strict=True)

class Task(BaseModel):
    id: int
    title: str
    done: bool

@app.get("/health")
def health():
    with database() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok"}

@app.get("/metrics")
def prometheus():
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})

@app.get("/", response_class=HTMLResponse)
def index():
    return Path(__file__).with_name("index.html").read_text()

@app.get("/api/tasks", response_model=list[Task])
def list_tasks():
    with database() as db:
        return [dict(row) for row in db.execute("SELECT * FROM tasks ORDER BY id")]

@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(task: TaskInput):
    with database() as db:
        cursor = db.execute("INSERT INTO tasks (title) VALUES (?)", (task.title,))
        return dict(db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone())

@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskUpdate):
    with database() as db:
        cursor = db.execute("UPDATE tasks SET done = ? WHERE id = ?", (task.done, task_id))
        if not cursor.rowcount:
            raise HTTPException(404, "Task not found")
        return dict(db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())

@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    with database() as db:
        cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if not cursor.rowcount:
            raise HTTPException(404, "Task not found")
    return Response(status_code=204)
