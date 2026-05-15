from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "evoting.db"))
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
POSTGRES_SCHEMA_PATH = BASE_DIR / "database" / "schema_postgres.sql"
KEY_DIR = BASE_DIR / "database" / "keys"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-session-secret-change-me")
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "20"))
IS_PRODUCTION = os.getenv("FLASK_ENV") == "production" or os.getenv("RENDER") == "true"
SESSION_COOKIE_SECURE = os.getenv(
    "SESSION_COOKIE_SECURE",
    "true" if IS_PRODUCTION else "false",
).lower() in {"1", "true", "yes", "on"}
EXPOSE_DEV_OTP = os.getenv(
    "EXPOSE_DEV_OTP",
    "false" if IS_PRODUCTION else "true",
).lower() in {"1", "true", "yes", "on"}
AUTO_SEED_ON_STARTUP = os.getenv("AUTO_SEED_ON_STARTUP", "false").lower() in {"1", "true", "yes", "on"}

# AES-256 key. For production this must be supplied through a secret manager.
_VOTE_ENCRYPTION_KEY_VALUE = os.getenv(
    "VOTE_ENCRYPTION_KEY",
    "change-this-32-byte-demo-key-1234",
)
VOTE_ENCRYPTION_KEY = _VOTE_ENCRYPTION_KEY_VALUE[:32].encode("utf-8")
VOTE_RSA_PRIVATE_KEY = os.getenv("VOTE_RSA_PRIVATE_KEY")
VOTE_RSA_PUBLIC_KEY = os.getenv("VOTE_RSA_PUBLIC_KEY")

OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5000")

if IS_PRODUCTION:
    if SECRET_KEY == "dev-session-secret-change-me":
        raise RuntimeError("Set SECRET_KEY before deploying to production.")
    if _VOTE_ENCRYPTION_KEY_VALUE == "change-this-32-byte-demo-key-1234" or len(_VOTE_ENCRYPTION_KEY_VALUE) < 32:
        raise RuntimeError("Set VOTE_ENCRYPTION_KEY to at least 32 characters before deploying.")
    if not VOTE_RSA_PRIVATE_KEY:
        raise RuntimeError("Set VOTE_RSA_PRIVATE_KEY before deploying to production.")
