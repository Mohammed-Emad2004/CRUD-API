from abc import ABC, abstractmethod


class TaskRepository(ABC):

    @abstractmethod
    def get_all(self) -> list[dict]:
        pass

    @abstractmethod
    def get_by_id(self, task_id: int) -> dict | None:
        pass

    @abstractmethod
    def create(self, title: str) -> dict:
        pass

    @abstractmethod
    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        pass

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        pass
