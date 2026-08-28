from pydantic import BaseModel


class Task(BaseModel):
    title: str


class UpdateTask(BaseModel):
    title: str | None = None
    done: bool | None = None


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    message: str | None = None
