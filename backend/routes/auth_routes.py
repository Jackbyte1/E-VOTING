from datetime import datetime, timezone

from flask import Blueprint, request, session

from backend.models.user_model import create_user, find_user_by_email, find_user_by_id
from backend.config import EXPOSE_DEV_OTP
from backend.services.audit_service import record_audit
from backend.services.otp_service import create_otp_session, verify_otp
from backend.services.security_service import hash_password, verify_password
from backend.utils.db import is_integrity_error
from backend.utils.responses import error, success

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id or not session.get("otp_verified"):
        return success({"authenticated": False, "role": None})

    user = find_user_by_id(user_id)
    if not user:
        session.clear()
        return success({"authenticated": False, "role": None})

    return success(
        {
            "authenticated": True,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
            "role": user["role"],
        }
    )


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = "student"
    institution_id = None
    reg_number = data.get("reg_number", "").strip() or None
    course = data.get("course", "").strip() or None

    if not name or not email or not password:
        return error("Name, email, and password are required.")
    if len(password) < 8:
        return error("Password must be at least 8 characters long.")

    try:
        user_id = create_user(name, email, hash_password(password), role, institution_id, reg_number, course)
        record_audit(f"REGISTER_USER:{email}:{role}", user_id)
    except Exception as exc:
        if is_integrity_error(exc):
            return error("An account with this email already exists.", 409)
        raise

    return success({"user_id": user_id}, "Registration successful.", 201)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = find_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return error("Invalid email or password.", 401)

    session.clear()
    session["pending_user_id"] = user["id"]
    session["pending_role"] = user["role"]
    otp_code = create_otp_session(user["id"])
    record_audit("LOGIN_PASSWORD_ACCEPTED_OTP_SENT", user["id"])

    response_data = {
        "user_id": user["id"],
        "role": user["role"],
    }
    if EXPOSE_DEV_OTP:
        response_data["dev_otp"] = otp_code

    return success(
        response_data,
        "Password accepted. Verify OTP to continue.",
    )


@auth_bp.post("/verify-otp")
def verify_otp_route():
    data = request.get_json(silent=True) or {}
    otp_code = data.get("otp_code", "").strip()
    pending_user_id = session.get("pending_user_id")

    if not pending_user_id:
        return error("No pending login session found.", 401)
    if not otp_code:
        return error("OTP code is required.")
    if not verify_otp(pending_user_id, otp_code):
        record_audit("OTP_VERIFICATION_FAILED", pending_user_id)
        return error("Invalid or expired OTP.", 401)

    session["user_id"] = pending_user_id
    session["role"] = session.get("pending_role", "student")
    session["otp_verified"] = True
    session["last_seen"] = datetime.now(timezone.utc).isoformat()
    session.pop("pending_user_id", None)
    session.pop("pending_role", None)
    record_audit("OTP_VERIFICATION_SUCCESS", session["user_id"])

    return success(
        {"user_id": session["user_id"], "role": session["role"]},
        "OTP verified successfully.",
    )


@auth_bp.post("/logout")
def logout():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        record_audit("LOGOUT", user_id)
    return success(message="Logged out.")
