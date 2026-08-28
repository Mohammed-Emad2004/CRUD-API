# FastAPI Task API

A full-stack backend application demonstrating **FastAPI**, **PostgreSQL**, **Docker Compose**, and **Supabase Authentication** with JWT/Bearer token verification, protected routes, and Swagger UI documentation.

---

## Features

- CRUD task API with full REST endpoints
- PostgreSQL persistence with Docker Compose
- Supabase Authentication (signup, login, logout)
- JWT/Bearer token verification
- Public and protected routes
- Reusable FastAPI authentication dependency
- Swagger UI with Bearer authentication support
- Repository abstraction pattern
- Persistent Docker volumes

---

## Architecture

### Task CRUD Flow

```text
HTTP Request
    ↓
Router
    ↓
TaskService
    ↓
TaskRepository
    ↓
PostgresTaskRepository
    ↓
PostgreSQL
```

### Authentication Flow

```text
Client
    ↓
Bearer Token
    ↓
get_current_user (FastAPI Dependency)
    ↓
Supabase Auth (get_user)
    ↓
Verified User
    ↓
Protected Route
```

Authentication logic is centralized in a single reusable FastAPI dependency (`app/auth_dependency.py`). All protected endpoints use `Depends(get_current_user)` to verify tokens through Supabase before executing route logic.

---

## Environment Setup

### 1. Create `.env` from the template

```bash
cp .env.example .env
```

### 2. Add your Supabase credentials

Edit `.env` and replace the placeholders with your own Supabase project values:

```text
DATABASE_URL=postgresql://user:password@localhost:5433/tasksdb

SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
```

**Important:**
- `.env` must **never** be committed to Git (it is gitignored).
- You must use your own Supabase project credentials.
- `.env.example` is safe to commit because it contains only placeholders.

---

## Supabase Setup

1. Create a free account at [supabase.com](https://supabase.com).
2. Create a new project.
3. Go to **Settings > API** and copy:
   - **Project URL** → put into `SUPABASE_URL` in `.env`
   - **Anon/public key** → put into `SUPABASE_KEY` in `.env`
4. Use your own Supabase project — do not share credentials.

---

## Installation / Running

### Start with Docker Compose

```bash
docker compose up --build
```

This starts both services:
- **FastAPI** application on port `8000`
- **PostgreSQL** database on port `5433`

### Access the application

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI |

### Data persistence

PostgreSQL data is persisted in a Docker named volume (`pgdata`). The database and `tasks` table are created automatically on first startup.

**Safe restart** (preserves data):

```bash
docker compose down
docker compose up -d
```

**Do not use** `docker compose down -v` — the `-v` flag removes the volume and destroys all data.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/dfhhgh/FAstapi.git
cd FAstapi

# 2. Create your .env file
cp .env.example .env
# Edit .env and add your Supabase credentials

# 3. Start with Docker Compose
docker compose up --build

# 4. Open Swagger UI
# http://localhost:8000/docs
```

---

## API Reference

| Method | Endpoint | Authentication | Description |
|--------|----------|----------------|-------------|
| GET | `/` | Public | API information |
| GET | `/health` | Public | Health check |
| GET | `/public/info` | Public | Public welcome message |
| GET | `/tasks` | Public | Get all tasks |
| GET | `/tasks/{id}` | Public | Get a task by ID |
| POST | `/tasks` | Public | Create a new task |
| PUT | `/tasks/{id}` | Public | Update a task |
| DELETE | `/tasks/{id}` | Public | Delete a task |
| POST | `/auth/signup` | Public | Create a new user account |
| POST | `/auth/login` | Public | Log in and receive access token |
| POST | `/auth/logout` | Bearer | Log out and invalidate session |
| GET | `/protected/profile` | Bearer | Get verified user profile |
| GET | `/protected/dashboard` | Bearer | Get dashboard with user ID |

---

## Authentication

Protected endpoints require a Bearer token in the `Authorization` header:

```text
Authorization: Bearer <access_token>
```

The token is verified through Supabase Auth before protected route logic executes. If the token is missing, malformed, or invalid, the API returns `401` with:

```json
{"error": "Access token required"}
```

or:

```json
{"error": "Invalid or expired token"}
```

---

## Swagger UI

Open `http://localhost:8000/docs` to access the interactive Swagger UI.

### Using Swagger with authentication

1. Log in through `POST /auth/login` with your email and password.
2. Copy the `access_token` from the response.
3. Click the **Authorize** button at the top of the Swagger UI.
4. Enter your token in the Bearer authentication field.
5. Click **Authorize**.
6. You can now test protected endpoints directly from Swagger.

![Swagger UI](images/Screenshot_22-7-2026_221724_127.0.0.1.jpeg)

---

## Docker Architecture

```text
FastAPI container
      |
      | db:5432
      ↓
PostgreSQL container
      |
      ↓
Docker named volume: pgdata
```

The FastAPI container connects to PostgreSQL using the Docker Compose service name `db`. The PostgreSQL container persists data in the named volume `pgdata`, which survives container restarts and recreation.

---

## Project Structure

```text
app/
├── main.py                 # FastAPI application setup, router wiring
├── router.py               # Task CRUD routes
├── service.py              # Task business logic
├── repository.py           # Abstract TaskRepository interface
├── postgres_repository.py  # PostgreSQL implementation
├── postgres_connection.py  # Database connection from environment
├── models.py               # Pydantic request/response models
├── supabase_client.py      # Supabase client initialization
├── auth_dependency.py      # Reusable authentication dependency
├── auth_error.py           # Custom AuthError exception
├── auth_router.py          # Signup, login, logout endpoints
├── gates_router.py         # Public and protected route endpoints
├── database.py             # (legacy SQLite connection)
├── sqlite_repository.py    # (legacy SQLite implementation)
├── __init__.py
Dockerfile
docker-compose.yml
sql/
├── init.sql                # Database initialization script
.env.example                # Environment variable template
.gitignore
README.md
requirment.txt              # Python dependencies
```

---

## A2 Historical Reference

In A2, the application used SQLite as its storage backend. The current A3+ architecture uses PostgreSQL. The legacy A2 setup is documented here for historical reference.

```bash
# A2 setup (historical — not the primary way to run)
pip install -r requirment.txt
uvicorn Fast:app --reload
```

A2 storage flow:

```text
SQLiteTaskRepository → SQLite (tasks.db)
```

Current A3+ storage flow:

```text
PostgresTaskRepository → PostgreSQL (Docker)
```

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| PostgreSQL 16 | Persistent database |
| Docker Compose | Container orchestration |
| Supabase | Authentication service |
| Pydantic | Data validation |
| psycopg | PostgreSQL adapter |
| Uvicorn | ASGI server |

---

## License

This project is for educational purposes.
