from typing import List, Dict
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small in-memory CRUD API for managing tasks.",
)

# In-memory storage for the task list.
tasks: List[Dict[str, object]] = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Write report", "done": True},
    {"id": 3, "title": "Call mom", "done": False},
]


@app.get("/", summary="API information")
async def root() -> dict:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
async def list_tasks() -> List[Dict[str, object]]:
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task")
async def get_task(task_id: int) -> JSONResponse:
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return JSONResponse(status_code=200, content=task)


@app.post("/tasks", status_code=201, summary="Create a task")
async def create_task(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Request body must be valid JSON"})

    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required and must be a non-empty string"},
        )

    new_task = {"id": max(item["id"] for item in tasks) + 1, "title": title.strip(), "done": False}
    tasks.append(new_task)
    return JSONResponse(status_code=201, content=new_task)


@app.put("/tasks/{task_id}", summary="Update a task")
async def update_task(task_id: int, request: Request) -> JSONResponse:
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Request body must be valid JSON"})

    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    if "title" not in payload and "done" not in payload:
        return JSONResponse(status_code=400, content={"error": "At least one of title or done must be provided"})

    if "title" in payload:
        title = payload["title"]
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(status_code=400, content={"error": "Title must be a non-empty string"})
        task["title"] = title.strip()

    if "done" in payload:
        done = payload["done"]
        if not isinstance(done, bool):
            return JSONResponse(status_code=400, content={"error": "Done must be a boolean"})
        task["done"] = done

    return JSONResponse(status_code=200, content=task)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def delete_task(task_id: int) -> Response:
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})

    tasks.remove(task)
    return Response(status_code=204)
