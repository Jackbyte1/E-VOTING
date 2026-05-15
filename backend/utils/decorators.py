from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import session

from backend.config import SESSION_TIMEOUT_MINUTES
from backend.utils.responses import error


def _session_is_fresh() -> bool:
    last_seen = session.get("last_seen")
    if not last_seen:
        return True
    try:
        last_seen_at = datetime.fromisoformat(last_seen)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - last_seen_at <= timedelta(minutes=SESSION_TIMEOUT_MINUTES)


def _touch_session() -> None:
    session["last_seen"] = datetime.now(timezone.utc).isoformat()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or not session.get("otp_verified"):
            return error("Authentication and OTP verification are required.", 401)
        if not _session_is_fresh():
            session.clear()
            return error("Session expired. Please log in again.", 401)
        _touch_session()
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id") or not session.get("otp_verified"):
            return error("Authentication and OTP verification are required.", 401)
        if not _session_is_fresh():
            session.clear()
            return error("Session expired. Please log in again.", 401)
        if session.get("role") != "admin":
            return error("Admin privileges are required.", 403)
        _touch_session()
        return view(*args, **kwargs)

    return wrapped
