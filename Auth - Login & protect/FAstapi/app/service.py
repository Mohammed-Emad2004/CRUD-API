from fastapi import HTTPException

from app.repository import TaskRepository


class TaskService:

    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def get_all_tasks(self) -> list[dict]:
        return self.repository.get_all()

    def get_task_by_id(self, task_id: int) -> dict:
        task = self.repository.get_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    def create_task(self, title: str) -> dict:
        if not title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        return self.repository.create(title.strip())

    def update_task(self, task_id: int, title: str | None, done: bool | None) -> dict:
        task = self.repository.update(task_id, title, done)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    def delete_task(self, task_id: int) -> None:
        deleted = self.repository.delete(task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Unknown id ")
