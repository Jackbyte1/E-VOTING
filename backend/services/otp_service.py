from datetime import datetime, timedelta, timezone

from backend.config import OTP_EXPIRY_MINUTES
from backend.services.email_service import send_otp_email
from backend.services.security_service import generate_otp
from backend.utils.db import get_connection


def create_otp_session(user_id: int, recipient_email: str, recipient_name: str | None = None) -> str:
    otp_code = generate_otp()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO otp_sessions (user_id, otp_code, expiry_time, is_used)
            VALUES (?, ?, ?, 0)
            """,
            (user_id, otp_code, expiry.isoformat()),
        )
    send_otp_email(recipient_email, recipient_name, otp_code, OTP_EXPIRY_MINUTES)
    return otp_code


def verify_otp(user_id: int, otp_code: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        otp = conn.execute(
            """
            SELECT * FROM otp_sessions
            WHERE user_id = ? AND otp_code = ? AND is_used = 0 AND expiry_time >= ?
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, otp_code, now),
        ).fetchone()
        if not otp:
            return False
        conn.execute("UPDATE otp_sessions SET is_used = 1 WHERE id = ?", (otp["id"],))
        return True
