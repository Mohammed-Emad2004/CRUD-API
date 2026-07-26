# Task API

This project is a small FastAPI CRUD API for managing a simple in-memory to-do list.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

4. Open the Swagger UI at http://127.0.0.1:8000/docs.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | / | API information |
| GET | /health | Health check |
| GET | /tasks | List all tasks |
| GET | /tasks/{id} | Get one task |
| POST | /tasks | Create a task |
| PUT | /tasks/{id} | Update a task |
| DELETE | /tasks/{id} | Delete a task |

## Example curl

```bash
curl -i http://127.0.0.1:8000/tasks/1
```

Example response:

```text
HTTP/1.1 200 OK
content-type: application/json

{"id":1,"title":"Buy groceries","done":false}
```

## Swagger screenshot

See the interactive API docs at http://127.0.0.1:8000/docs and the screenshot in the docs folder.
