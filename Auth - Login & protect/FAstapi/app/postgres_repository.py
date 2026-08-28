from app.repository import TaskRepository
from app.postgres_connection import get_connection


class PostgresTaskRepository(TaskRepository):

    def get_all(self) -> list[dict]:
        conn = get_connection()
        cur = conn.execute("SELECT id, title, done FROM tasks")
        rows = cur.fetchall()
        conn.close()
        return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]

    def get_by_id(self, task_id: int) -> dict | None:
        conn = get_connection()
        cur = conn.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "title": row[1], "done": row[2]}
        return None

    def create(self, title: str) -> dict:
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
            (title, False),
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return {"id": row[0], "title": row[1], "done": row[2]}

    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        conn = get_connection()
        cur = conn.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        current_title = row[1]
        current_done = row[2]
        new_title = title if (title is not None and title.strip()) else current_title
        new_done = done if done is not None else current_done
        cur = conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
            (new_title, new_done, task_id),
        )
        updated = cur.fetchone()
        conn.commit()
        conn.close()
        return {"id": updated[0], "title": updated[1], "done": updated[2]}

    def delete(self, task_id: int) -> bool:
        conn = get_connection()
        cur = conn.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        conn.close()
        return True
