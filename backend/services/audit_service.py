from datetime import datetime, timezone

from backend.services.security_service import sha256_hash
from backend.utils.db import get_connection

GENESIS_HASH = "0" * 64


def record_audit(action: str, user_id=None, merkle_root=None) -> str:
    """Append a tamper-evident audit log using simple hash chaining."""

    timestamp = datetime.now(timezone.utc).isoformat()

    # Normalize optional fields for stable hashing
    normalized_user_id = "" if user_id is None else str(user_id)
    normalized_merkle_root = "" if merkle_root is None else str(merkle_root)

    with get_connection() as conn:
        last_log = conn.execute(
            "SELECT current_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        previous_hash = (
            last_log["current_hash"]
            if last_log
            else GENESIS_HASH
        )

        current_hash = sha256_hash(
            f"{action}|{normalized_user_id}|{timestamp}|{previous_hash}|{normalized_merkle_root}"
        )

        conn.execute(
            """
            INSERT INTO audit_logs
            (action, user_id, timestamp, previous_hash, current_hash, merkle_root)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                user_id,
                timestamp,
                previous_hash,
                current_hash,
                merkle_root,
            ),
        )

        return current_hash