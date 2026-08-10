import sqlite3
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
app=FastAPI()

def init_db():
    conn = sqlite3.connect("tasks.db")
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

tasks = [
    {
        "id": 1,
        "title": "Study FastAPI",
        "done": False
    },
    {
        "id": 2,
        "title": "Read book",
        "done": True
    },
    {
        "id": 3,
        "title": "Go to gym",
        "done": False
    }
]
@app.get(
    "/tasks",
    summary="Get all tasks",
    description="Returns a list of all tasks."
)
async def gettasks():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]

@app.get('/tasks/{id}')
async def gettask(id:int):
    conn = sqlite3.connect("tasks.db")
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
        tasks.append(
        {
            "id":tasks[-1]["id"] + 1,
            "title": task.title,
            "done": False
        }
        )
        return tasks[-1]
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
    for task in tasks:
            if task['id']==id:
                if Update.title is not None and Update.title.strip():
                  task['title']=Update.title
                if Update.done is not None:
                  task['done']=Update.done
                return task

    raise HTTPException (status_code=404, detail=f"Task {id} not found" )
    
        


@app.delete(
    "/tasks/{id}",
    summary="Delete a task",
    description="Deletes a task by its ID.",
    status_code=204
)
async def deletetask(id:int):
        for task in tasks:
            if task['id']==id:
                tasks.remove(task)
                return 
        raise HTTPException (status_code=404, detail="Unknown id "  )
    
