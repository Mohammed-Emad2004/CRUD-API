from typing import List, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Task API", version="1.0")

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
