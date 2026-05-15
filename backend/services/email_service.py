import resend

from backend.config import RESEND_API_KEY

resend.api_key = RESEND_API_KEY


class EmailDeliveryError(RuntimeError):
    pass


def send_otp_email(recipient_email, recipient_name, otp_code, expiry_minutes):
    try:
        resend.Emails.send({
            "from": "SecureVote <onboarding@resend.dev>",
            "to": recipient_email,
            "subject": "Your SecureVote verification code",
            "html": f"""
                <h2>Your OTP Code</h2>
                <p>Hello {recipient_name or "User"},</p>
                <p>Your verification code is:</p>
                <h1>{otp_code}</h1>
                <p>Expires in {expiry_minutes} minutes.</p>
            """
        })

    except Exception as exc:
        print("RESEND ERROR:", repr(exc))
        raise EmailDeliveryError("Could not send OTP email.") from exc