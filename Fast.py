import sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
app=FastAPI()

DB_PATH = Path(__file__).resolve().parent / "tasks.db"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            done BOOLEAN
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        sample_tasks = [
            (1, "Study FastAPI", False),
            (2, "Read book", True),
            (3, "Go to gym", False),
        ]
        cursor.executemany("INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)", sample_tasks)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get('/')
async def root():
    return { "name": "Task API", "version": "1.0", "endpoints": ["/tasks"] }

class Task(BaseModel):
    title:str
@app.get('/health')
async def health():
    return { "status": "ok" }

@app.get(
    "/tasks",
    summary="Get all tasks",
    description="Returns a list of all tasks."
)
async def gettasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]

@app.get('/tasks/{id}')
async def gettask(id:int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "title": row[1], "done": row[2]}
    raise HTTPException (status_code=404, detail=f"Task {id} not found" )

@app.post(
    "/tasks",
    summary="Create a task",
    description="Creates a new task and returns it.",
    status_code=201
)
async def posttask(task:Task):
    if   task.title.strip():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (task.title.strip(), False))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return {"id": row[0], "title": row[1], "done": row[2]}
    raise HTTPException (status_code=400, detail="Title cannot be empty"  )
class UpdateTask(BaseModel):
    title:str|None=None
    done:bool|None=None

@app.put(
    "/tasks/{id}",
    summary="Update a task",
    description="Updates an existing task."
)
async def puttask(id:int,Update:UpdateTask):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException (status_code=404, detail=f"Task {id} not found" )
    current_title = row[1]
    current_done = row[2]
    new_title = Update.title if (Update.title is not None and Update.title.strip()) else current_title
    new_done = Update.done if Update.done is not None else current_done
    cursor.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (new_title, new_done, id))
    conn.commit()
    conn.close()
    return {"id": id, "title": new_title, "done": new_done}

@app.delete(
    "/tasks/{id}",
    summary="Delete a task",
    description="Deletes a task by its ID.",
    status_code=204
)
async def deletetask(id:int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException (status_code=404, detail="Unknown id "  )
    cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return
