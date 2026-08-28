from app.repository import TaskRepository
from app.database import get_db_connection


class SQLiteTaskRepository(TaskRepository):

    def get_all(self) -> list[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]

    def get_by_id(self, task_id: int) -> dict | None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "title": row[1], "done": row[2]}
        return None

    def create(self, title: str) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, False))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        conn.close()
        return {"id": row[0], "title": row[1], "done": row[2]}

    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        current_title = row[1]
        current_done = row[2]
        new_title = title if (title is not None and title.strip()) else current_title
        new_done = done if done is not None else current_done
        cursor.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (new_title, new_done, task_id))
        conn.commit()
        conn.close()
        return {"id": task_id, "title": new_title, "done": new_done}

    def delete(self, task_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True
