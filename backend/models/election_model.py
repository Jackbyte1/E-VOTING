from backend.utils.db import get_connection, insert_and_get_id, query_all, query_one


def create_election(title: str, start_date: str, end_date: str, created_by: int | None = None) -> int:
    with get_connection() as conn:
        return insert_and_get_id(
            conn,
            """
            INSERT INTO elections (title, start_date, end_date, status, is_active, created_by)
            VALUES (?, ?, ?, 'closed', 0, ?)
            """,
            (title, start_date, end_date, created_by),
        )


def add_candidate(name: str, election_id: int, position: str, manifesto: str | None = None) -> int:
    with get_connection() as conn:
        return insert_and_get_id(
            conn,
            """
            INSERT INTO candidates (name, election_id, position, manifesto)
            VALUES (?, ?, ?, ?)
            """,
            (name, election_id, position, manifesto),
        )


def set_election_active(election_id: int, is_active: bool) -> None:
    with get_connection() as conn:
        if is_active:
            # Prototype policy: one active election at a time for a simpler voting UX.
            conn.execute("UPDATE elections SET is_active = 0, status = 'closed'")
        conn.execute(
            "UPDATE elections SET is_active = ?, status = ? WHERE id = ?",
            (1 if is_active else 0, "open" if is_active else "closed", election_id),
        )


def get_active_election():
    return query_one("SELECT * FROM elections WHERE is_active = 1 ORDER BY id DESC LIMIT 1")


def get_election(election_id: int):
    return query_one("SELECT * FROM elections WHERE id = ?", (election_id,))


def get_all_elections():
    return query_all("SELECT * FROM elections ORDER BY id DESC")


def get_candidates_for_election(election_id: int):
    return query_all(
        "SELECT * FROM candidates WHERE election_id = ? ORDER BY position, name",
        (election_id,),
    )
