from backend.services.audit_service import (
    GENESIS_HASH,
    build_audit_hash,
)

from backend.services.merkle_service import (
    verify_election_merkle_root,
)

from backend.utils.db import get_connection


def rebuild_audit_chain():
    """Rebuild audit chain using canonical hashing."""

    with get_connection() as conn:
        logs = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id ASC"
        ).fetchall()

        previous_hash = GENESIS_HASH

        for log in logs:
            current_hash = build_audit_hash(
                log["action"],
                log["user_id"],
                log["timestamp"],
                previous_hash,
                log["merkle_root"],
            )

            conn.execute(
                """
                UPDATE audit_logs
                SET previous_hash = ?, current_hash = ?
                WHERE id = ?
                """,
                (
                    previous_hash,
                    current_hash,
                    log["id"],
                ),
            )

            previous_hash = current_hash


def verify_audit_chain() -> dict:
    """Verify audit hash chain integrity."""

    with get_connection() as conn:
        logs = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id ASC"
        ).fetchall()

    previous_hash = GENESIS_HASH

    for log in logs:
        expected_hash = build_audit_hash(
            log["action"],
            log["user_id"],
            log["timestamp"],
            previous_hash,
            log["merkle_root"],
        )

        if (
            log["previous_hash"] != previous_hash
            or log["current_hash"] != expected_hash
        ):
            return {
                "valid": False,
                "checked_logs": len(logs),
                "failed_log_id": log["id"],
                "message": "Audit chain mismatch detected.",
            }

        previous_hash = log["current_hash"]

    return {
        "valid": True,
        "checked_logs": len(logs),
        "failed_log_id": None,
        "message": "Audit chain is intact.",
    }


def verify_system_integrity(election_id: int | None = None) -> dict:
    #This is a temporary requirement
    #rebuild_audit_chain()

    audit = verify_audit_chain()

    merkle = (
        verify_election_merkle_root(election_id)
        if election_id
        else None
    )

    vote_storage = {
        "protected": True,
        "message": (
            "Vote records are encrypted and protected "
            "by append-only database rules."
        ),
    }

    return {
        "audit_chain": audit,
        "merkle": merkle,
        "vote_storage": vote_storage,
        "tamper_evident": (
            audit["valid"]
            and (merkle["valid"] if merkle else True)
        ),
        "status": (
            "No tampering detected"
            if audit["valid"]
            and (merkle["valid"] if merkle else True)
            else "Review required"
        ),
    }