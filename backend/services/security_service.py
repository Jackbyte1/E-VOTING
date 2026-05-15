import base64
import hashlib
import json
import secrets

import bcrypt
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA

from backend.config import KEY_DIR, VOTE_ENCRYPTION_KEY, VOTE_RSA_PRIVATE_KEY, VOTE_RSA_PUBLIC_KEY


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_pem(value: str) -> bytes:
    """Support Render env vars pasted with escaped newlines."""
    return value.replace("\\n", "\n").encode("utf-8")


def get_or_create_rsa_keypair() -> tuple[RSA.RsaKey, RSA.RsaKey]:
    """Load RSA keys from env vars or local files, then create local dev keys."""
    if VOTE_RSA_PRIVATE_KEY:
        private_key = RSA.import_key(_normalize_pem(VOTE_RSA_PRIVATE_KEY))
        public_key = (
            RSA.import_key(_normalize_pem(VOTE_RSA_PUBLIC_KEY))
            if VOTE_RSA_PUBLIC_KEY
            else private_key.publickey()
        )
        return private_key, public_key

    KEY_DIR.mkdir(parents=True, exist_ok=True)
    private_path = KEY_DIR / "vote_private.pem"
    public_path = KEY_DIR / "vote_public.pem"

    if private_path.exists() and public_path.exists():
        private_key = RSA.import_key(private_path.read_bytes())
        public_key = RSA.import_key(public_path.read_bytes())
        return private_key, public_key

    private_key = RSA.generate(2048)
    public_key = private_key.publickey()
    private_path.write_bytes(private_key.export_key("PEM"))
    public_path.write_bytes(public_key.export_key("PEM"))
    return private_key, public_key


def encrypt_vote(vote_payload: dict) -> tuple[str, str]:
    """Encrypt vote data with AES-GCM and wrap the AES key with RSA-OAEP."""
    _, public_key = get_or_create_rsa_keypair()
    aes_key = get_random_bytes(32)
    nonce = get_random_bytes(12)
    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    plaintext = json.dumps(vote_payload, sort_keys=True).encode("utf-8")
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    encrypted_key = PKCS1_OAEP.new(public_key).encrypt(aes_key)
    encrypted = {
        "algorithm": "AES-256-GCM",
        "key_wrap": "RSA-2048-OAEP",
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "tag": base64.b64encode(tag).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
    }
    return json.dumps(encrypted, sort_keys=True), base64.b64encode(encrypted_key).decode("utf-8")


def blind_voter_hash(user_id: int, election_id: int, position: str) -> str:
    """Pseudonymize a voter-position relation for auditability without exposing raw identity."""
    salt = base64.b64encode(VOTE_ENCRYPTION_KEY).decode("utf-8")
    return sha256_hash(f"{salt}|{user_id}|{election_id}|{position}")
