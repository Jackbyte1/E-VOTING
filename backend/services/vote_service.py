from datetime import datetime, timezone

from backend.services.security_service import blind_voter_hash, encrypt_vote, sha256_hash
from backend.utils.db import get_connection, is_integrity_error


def has_user_voted(user_id: int, election_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM votes WHERE user_id = ? AND election_id = ?",
            (user_id, election_id),
        ).fetchone()
        return row is not None


def get_user_voted_positions(user_id: int, election_id: int) -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT position FROM votes WHERE user_id = ? AND election_id = ?",
            (user_id, election_id),
        ).fetchall()
    return {row["position"] for row in rows}


def cast_vote(user_id: int, election_id: int, candidate_id: int, position: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    vote_payload = {
        "user_id": user_id,
        "election_id": election_id,
        "candidate_id": candidate_id,
        "position": position,
        "timestamp": timestamp,
    }
    encrypted_vote, encrypted_key = encrypt_vote(vote_payload)
    voter_blind_hash = blind_voter_hash(user_id, election_id, position)
    vote_hash = sha256_hash(f"{user_id}|{election_id}|{candidate_id}|{position}|{timestamp}|{encrypted_vote}")

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO votes (
                    user_id, candidate_id, election_id, position, voter_blind_hash,
                    encrypted_vote, encrypted_key, vote_hash, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    candidate_id,
                    election_id,
                    position,
                    voter_blind_hash,
                    encrypted_vote,
                    encrypted_key,
                    vote_hash,
                    timestamp,
                ),
            )
            conn.execute("UPDATE users SET has_voted = 1 WHERE id = ?", (user_id,))
    except Exception as exc:
        if is_integrity_error(exc):
            raise ValueError("Duplicate vote detected or invalid voting data.") from exc
        raise

    return vote_hash


def cast_ballot(user_id: int, election_id: int, selections: list[dict]) -> list[dict]:
    """Cast one encrypted vote for each selected position in a single transaction."""
    if not selections:
        raise ValueError("At least one candidate selection is required.")

    vote_receipts = []
    seen_positions = set()
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as conn:
            for selection in selections:
                candidate_id = int(selection["candidate_id"])
                candidate = conn.execute(
                    "SELECT * FROM candidates WHERE id = ? AND election_id = ?",
                    (candidate_id, election_id),
                ).fetchone()
                if not candidate:
                    raise ValueError("A selected candidate does not belong to this election.")

                position = candidate["position"]
                if position in seen_positions:
                    raise ValueError(f"Only one candidate can be selected for {position}.")
                seen_positions.add(position)

                existing = conn.execute(
                    "SELECT id FROM votes WHERE user_id = ? AND election_id = ? AND position = ?",
                    (user_id, election_id, position),
                ).fetchone()
                if existing:
                    raise ValueError(f"You have already voted for {position}.")

                vote_payload = {
                    "user_id": user_id,
                    "election_id": election_id,
                    "candidate_id": candidate_id,
                    "position": position,
                    "timestamp": timestamp,
                }
                encrypted_vote, encrypted_key = encrypt_vote(vote_payload)
                voter_blind_hash = blind_voter_hash(user_id, election_id, position)
                vote_hash = sha256_hash(
                    f"{user_id}|{election_id}|{candidate_id}|{position}|{timestamp}|{encrypted_vote}"
                )
                conn.execute(
                    """
                    INSERT INTO votes (
                        user_id, candidate_id, election_id, position, voter_blind_hash,
                        encrypted_vote, encrypted_key, vote_hash, timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        candidate_id,
                        election_id,
                        position,
                        voter_blind_hash,
                        encrypted_vote,
                        encrypted_key,
                        vote_hash,
                        timestamp,
                    ),
                )
                vote_receipts.append(
                    {
                        "position": position,
                        "candidate_id": candidate_id,
                        "candidate_name": candidate["name"],
                        "vote_hash": vote_hash,
                    }
                )

            conn.execute("UPDATE users SET has_voted = 1 WHERE id = ?", (user_id,))
    except Exception as exc:
        if is_integrity_error(exc):
            raise ValueError("Duplicate vote detected or invalid voting data.") from exc
        raise

    return vote_receipts


def get_results(election_id: int | None = None) -> list[dict]:
    query = """
        SELECT
            e.id AS election_id,
            e.title AS election_title,
            c.id AS candidate_id,
            c.name AS candidate_name,
            c.position AS position,
            COUNT(v.id) AS vote_count
        FROM candidates c
        JOIN elections e ON e.id = c.election_id
        LEFT JOIN votes v ON v.candidate_id = c.id AND v.election_id = e.id
    """
    params = []
    if election_id:
        query += " WHERE e.id = ?"
        params.append(election_id)
    query += """
        GROUP BY e.id, e.title, c.id, c.name, c.position
        ORDER BY e.id DESC, c.position, vote_count DESC, c.name
    """

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    grouped_totals: dict[tuple[int, str], int] = {}
    for row in rows:
        key = (row["election_id"], row["position"])
        grouped_totals[key] = grouped_totals.get(key, 0) + row["vote_count"]

    return [
        {
            "election_id": row["election_id"],
            "election_title": row["election_title"],
            "candidate_id": row["candidate_id"],
            "candidate_name": row["candidate_name"],
            "position": row["position"],
            "vote_count": row["vote_count"],
            "total_votes": grouped_totals[(row["election_id"], row["position"])],
            "percentage": round(
                (row["vote_count"] / grouped_totals[(row["election_id"], row["position"])] * 100)
                if grouped_totals[(row["election_id"], row["position"])]
                else 0,
                2,
            ),
        }
        for row in rows
    ]


def get_election_stats(election_id: int | None = None) -> dict:
    with get_connection() as conn:
        student_count = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'student'").fetchone()["count"]
        candidate_query = "SELECT COUNT(*) AS count FROM candidates"
        vote_query = "SELECT COUNT(*) AS count FROM votes"
        voter_query = "SELECT COUNT(DISTINCT user_id) AS count FROM votes"
        params = ()
        if election_id:
            candidate_query += " WHERE election_id = ?"
            vote_query += " WHERE election_id = ?"
            voter_query += " WHERE election_id = ?"
            params = (election_id,)

        candidate_count = conn.execute(candidate_query, params).fetchone()["count"]
        votes_cast = conn.execute(vote_query, params).fetchone()["count"]
        voters_cast = conn.execute(voter_query, params).fetchone()["count"]

    turnout = round((voters_cast / student_count * 100) if student_count else 0, 2)
    return {
        "total_registered_voters": student_count,
        "votes_cast": votes_cast,
        "voters_cast": voters_cast,
        "turnout_percentage": turnout,
        "number_of_candidates": candidate_count,
    }


def verify_vote_hash(vote_hash: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM votes WHERE vote_hash = ?", (vote_hash,)).fetchone()
        return row is not None
