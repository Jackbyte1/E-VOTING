import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from backend.config import DATABASE_PATH, DATABASE_URL, POSTGRES_SCHEMA_PATH, SCHEMA_PATH


IS_POSTGRES = bool(DATABASE_URL)


class PostgresCursor:
    """Small adapter that lets existing SQLite-style code work with PostgreSQL."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql: str, params: Iterable = ()):
        self._cursor.execute(_prepare_sql(sql), tuple(params))
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class PostgresConnection:
    """Connection wrapper exposing a sqlite3-like execute API."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql: str, params: Iterable = ()):
        cursor = self._connection.cursor()
        cursor.execute(_prepare_sql(sql), tuple(params))
        return PostgresCursor(cursor)

    def executescript(self, script: str):
        cursor = self._connection.cursor()
        cursor.execute(script)
        return PostgresCursor(cursor)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def _prepare_sql(sql: str) -> str:
    """Translate SQLite placeholders and simple booleans for PostgreSQL."""
    if not IS_POSTGRES:
        return sql
    return sql.replace("?", "%s")


def get_connection():
    """Create a database connection.

    SQLite remains the local fallback. When DATABASE_URL is set, PostgreSQL is
    used for production-style deployments such as Render.
    """
    if IS_POSTGRES:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresConnection(conn)

    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize tables from the correct schema for the selected database."""
    with get_connection() as conn:
        schema_path = POSTGRES_SCHEMA_PATH if IS_POSTGRES else SCHEMA_PATH
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())
        if not IS_POSTGRES:
            apply_sqlite_migrations(conn)


def _sqlite_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def apply_sqlite_migrations(conn: sqlite3.Connection) -> None:
    """Small SQLite migrations for existing prototype databases."""
    user_columns = _sqlite_table_columns(conn, "users")
    if "institution_id" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN institution_id TEXT")
    if "reg_number" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN reg_number TEXT")
    if "course" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN course TEXT")

    election_columns = _sqlite_table_columns(conn, "elections")
    if "status" not in election_columns:
        conn.execute("ALTER TABLE elections ADD COLUMN status TEXT NOT NULL DEFAULT 'closed'")
        conn.execute("UPDATE elections SET status = CASE WHEN is_active = 1 THEN 'open' ELSE 'closed' END")
    if "created_by" not in election_columns:
        conn.execute("ALTER TABLE elections ADD COLUMN created_by INTEGER REFERENCES users(id)")

    candidate_columns = _sqlite_table_columns(conn, "candidates")
    if "manifesto" not in candidate_columns:
        conn.execute("ALTER TABLE candidates ADD COLUMN manifesto TEXT")

    audit_columns = _sqlite_table_columns(conn, "audit_logs")
    if "merkle_root" not in audit_columns:
        conn.execute("ALTER TABLE audit_logs ADD COLUMN merkle_root TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merkle_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_id INTEGER NOT NULL,
            merkle_root TEXT NOT NULL,
            computed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (election_id) REFERENCES elections (id)
        )
        """
    )

    vote_columns = _sqlite_table_columns(conn, "votes")
    needs_vote_rebuild = not {"position", "voter_blind_hash", "encrypted_key"}.issubset(vote_columns)
    if needs_vote_rebuild:
        # Rebuild votes to replace the v1 one-vote-per-election constraint with
        # one-vote-per-position while adding cryptographic metadata.
        conn.execute("ALTER TABLE votes RENAME TO votes_v1")
        conn.execute(
            """
            CREATE TABLE votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                election_id INTEGER NOT NULL,
                position TEXT NOT NULL,
                voter_blind_hash TEXT NOT NULL,
                encrypted_vote TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                vote_hash TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (candidate_id) REFERENCES candidates (id),
                FOREIGN KEY (election_id) REFERENCES elections (id),
                UNIQUE (user_id, election_id, position)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO votes (
                id, user_id, candidate_id, election_id, position, voter_blind_hash,
                encrypted_vote, encrypted_key, vote_hash, timestamp
            )
            SELECT
                v.id, v.user_id, v.candidate_id, v.election_id,
                COALESCE(c.position, 'General'),
                lower(hex(randomblob(32))),
                v.encrypted_vote,
                'legacy-key-not-wrapped',
                v.vote_hash, v.timestamp
            FROM votes_v1 v
            LEFT JOIN candidates c ON c.id = v.candidate_id
            """
        )
        conn.execute("DROP TABLE votes_v1")
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_vote_update
        BEFORE UPDATE ON votes
        BEGIN
            SELECT RAISE(ABORT, 'Votes are append-only and cannot be updated');
        END;
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_vote_delete
        BEFORE DELETE ON votes
        BEGIN
            SELECT RAISE(ABORT, 'Votes are append-only and cannot be deleted');
        END;
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_election ON votes (election_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_position ON votes (election_id, position)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_blind_hash ON votes (voter_blind_hash)")


def insert_and_get_id(conn, sql: str, params: Iterable = ()) -> int:
    """Insert a row and return its generated primary key for SQLite/PostgreSQL."""
    if IS_POSTGRES:
        cursor = conn.execute(f"{sql.strip()} RETURNING id", params)
        row = cursor.fetchone()
        return int(row["id"])
    cursor = conn.execute(sql, tuple(params))
    return int(cursor.lastrowid)


def is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    if IS_POSTGRES:
        import psycopg2

        return isinstance(exc, psycopg2.IntegrityError)
    return False


def query_one(sql: str, params: Iterable = ()) -> Optional[object]:
    with get_connection() as conn:
        return conn.execute(sql, tuple(params)).fetchone()


def query_all(sql: str, params: Iterable = ()) -> list[object]:
    with get_connection() as conn:
        return conn.execute(sql, tuple(params)).fetchall()
