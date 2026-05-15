from email.message import EmailMessage
from html import escape
import smtplib

from backend.config import (
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    OTP_DELIVERY_MODE,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TIMEOUT_SECONDS,
    SMTP_USERNAME,
    SMTP_USE_SSL,
    SMTP_USE_TLS,
)


class EmailDeliveryError(RuntimeError):
    """Raised when an OTP email cannot be sent."""


def _from_header() -> str:
    if EMAIL_FROM_NAME:
        return f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    return EMAIL_FROM


def send_otp_email(recipient_email: str, recipient_name: str | None, otp_code: str, expiry_minutes: int) -> None:
    """Send a login OTP through the configured SMTP provider."""
    if OTP_DELIVERY_MODE == "console":
        print(f"[SIMULATED EMAIL] {recipient_email} OTP: {otp_code}")
        return

    if OTP_DELIVERY_MODE != "smtp":
        raise EmailDeliveryError("Unsupported OTP delivery mode.")
    if not SMTP_HOST or not EMAIL_FROM:
        raise EmailDeliveryError("SMTP_HOST and EMAIL_FROM must be configured.")

    name = recipient_name or "student"
    safe_name = escape(name)
    message = EmailMessage()
    message["Subject"] = "Your SecureVote verification code"
    message["From"] = _from_header()
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                f"Hello {name},",
                "",
                f"Your SecureVote verification code is: {otp_code}",
                f"This code expires in {expiry_minutes} minutes.",
                "",
                "If you did not try to sign in, ignore this email and contact the election administrator.",
                "",
                "SecureVote",
            ]
        )
    )
    message.add_alternative(
        f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #0f172a;">
            <p>Hello {safe_name},</p>
            <p>Your SecureVote verification code is:</p>
            <p style="font-size: 28px; font-weight: 700; letter-spacing: 4px;">{otp_code}</p>
            <p>This code expires in {expiry_minutes} minutes.</p>
            <p>If you did not try to sign in, ignore this email and contact the election administrator.</p>
            <p>SecureVote</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
                _send(server, message)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                _send(server, message)
    except Exception as exc:
        raise EmailDeliveryError("Could not send OTP email.") from exc


def _send(server, message: EmailMessage) -> None:
    if SMTP_USERNAME and SMTP_PASSWORD:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.send_message(message)
