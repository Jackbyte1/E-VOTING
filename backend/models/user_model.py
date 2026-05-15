from backend.utils.db import get_connection, insert_and_get_id, query_one


def create_user(
    name: str,
    email: str,
    password_hash: str,
    role: str = "student",
    institution_id: str | None = None,
    reg_number: str | None = None,
    course: str | None = None,
) -> int:
    with get_connection() as conn:
        return insert_and_get_id(
            conn,
            """
            INSERT INTO users (name, email, institution_id, password_hash, role, reg_number, course)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, email.lower().strip(), institution_id, password_hash, role, reg_number, course),
        )


def find_user_by_email(email: str):
    return query_one("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))


def find_user_by_id(user_id: int):
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def list_users():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT id, name, email, institution_id, reg_number, course, role, has_voted, created_at
            FROM users
            ORDER BY role, name
            """
        ).fetchall()


def update_user_role(user_id: int, role: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
