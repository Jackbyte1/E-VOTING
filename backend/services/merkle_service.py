from datetime import datetime, timezone

from backend.services.security_service import sha256_hash
from backend.utils.db import get_connection


def build_merkle_root(hashes: list[str]) -> str:
    """Build a simple SHA-256 Merkle root from vote receipt hashes."""
    if not hashes:
        return sha256_hash("EMPTY_ELECTION")

    level = sorted(hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [sha256_hash(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def compute_and_store_election_merkle_root(election_id: int) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT vote_hash FROM votes WHERE election_id = ? ORDER BY vote_hash",
            (election_id,),
        ).fetchall()
        root = build_merkle_root([row["vote_hash"] for row in rows])
        conn.execute(
            """
            INSERT INTO merkle_roots (election_id, merkle_root, computed_at)
            VALUES (?, ?, ?)
            """,
            (election_id, root, timestamp),
        )
        return root


def get_latest_merkle_root(election_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM merkle_roots
            WHERE election_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (election_id,),
        ).fetchone()
        return dict(row) if row else None


def get_latest_merkle_root_any():
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT mr.*, e.title AS election_title
            FROM merkle_roots mr
            JOIN elections e ON e.id = mr.election_id
            ORDER BY mr.id DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


def verify_election_merkle_root(election_id: int) -> dict:
    latest = get_latest_merkle_root(election_id)
    if not latest:
        return {"published": False, "valid": False, "expected_root": None, "published_root": None}

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT vote_hash FROM votes WHERE election_id = ? ORDER BY vote_hash",
            (election_id,),
        ).fetchall()
    expected_root = build_merkle_root([row["vote_hash"] for row in rows])
    return {
        "published": True,
        "valid": expected_root == latest["merkle_root"],
        "expected_root": expected_root,
        "published_root": latest["merkle_root"],
        "computed_at": latest["computed_at"],
    }
