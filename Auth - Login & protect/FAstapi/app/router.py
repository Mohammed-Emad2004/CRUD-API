from fastapi import APIRouter, Depends

from app.models import Task, UpdateTask
from app.service import TaskService

router = APIRouter()


def get_task_service():
    from app.main import task_service
    return task_service


@router.get("/")
async def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get(
    "/tasks",
    summary="Get all tasks",
    description="Returns a list of all tasks.",
)
async def gettasks(service: TaskService = Depends(get_task_service)):
    return service.get_all_tasks()


@router.get("/tasks/{id}")
async def gettask(id: int, service: TaskService = Depends(get_task_service)):
    return service.get_task_by_id(id)


@router.post(
    "/tasks",
    summary="Create a task",
    description="Creates a new task and returns it.",
    status_code=201,
)
async def posttask(task: Task, service: TaskService = Depends(get_task_service)):
    return service.create_task(task.title)


@router.put(
    "/tasks/{id}",
    summary="Update a task",
    description="Updates an existing task.",
)
async def puttask(id: int, Update: UpdateTask, service: TaskService = Depends(get_task_service)):
    return service.update_task(id, Update.title, Update.done)


@router.delete(
    "/tasks/{id}",
    summary="Delete a task",
    description="Deletes a task by its ID.",
    status_code=204,
)
async def deletetask(id: int, service: TaskService = Depends(get_task_service)):
    service.delete_task(id)
