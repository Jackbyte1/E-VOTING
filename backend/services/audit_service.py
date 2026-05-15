from datetime import datetime, timezone

from backend.services.security_service import sha256_hash
from backend.utils.db import get_connection

GENESIS_HASH = "0" * 64


def normalize_merkle_root(merkle_root):
    return merkle_root if merkle_root is not None else "NO_MERKLE"


def record_audit(action: str, user_id=None, merkle_root=None) -> str:
    """Append a tamper-evident audit log using stable hash chaining."""

    timestamp = datetime.now(timezone.utc).isoformat()

    normalized_merkle = normalize_merkle_root(merkle_root)

    with get_connection() as conn:
        last_log = conn.execute(
            "SELECT current_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        previous_hash = (
            last_log["current_hash"] if last_log else GENESIS_HASH
        )

        payload = (
            f"{action}|{user_id}|{timestamp}|"
            f"{previous_hash}|{normalized_merkle}"
        )

        current_hash = sha256_hash(payload)

        conn.execute(
            """
            INSERT INTO audit_logs (
                action,
                user_id,
                timestamp,
                previous_hash,
                current_hash,
                merkle_root
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                user_id,
                timestamp,
                previous_hash,
                current_hash,
                normalized_merkle,
            ),
        )

        return current_hash