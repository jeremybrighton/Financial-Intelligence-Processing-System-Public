"""
FRC System — Security Utilities
==================================
Password hashing, JWT creation/decoding, API key generation.
"""
import hashlib
import hmac
import logging
import secrets
import smtplib
import string
import random
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

log = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Passwords ─────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def decode_token_safe(token: str) -> Optional[dict]:
    try:
        return decode_token(token)
    except JWTError:
        return None


# ── Institution API keys ──────────────────────────────────────────────────────

def generate_api_key(length: int = 48) -> str:
    """
    Generate a cryptographically secure institution API key.
    Format: frc_<48-char random alphanumeric>
    The raw key is shown ONCE at creation — only the hash is stored.
    """
    alphabet = string.ascii_letters + string.digits
    raw = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"frc_{raw}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), stored_hash)


def get_key_suffix(raw_key: str) -> str:
    """Last 6 chars for display — never the full key."""
    return raw_key[-6:]


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def send_otp_email(to_email: str, otp_code: str, purpose: str = "login") -> bool:
    if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD:
        log.warning("SMTP not configured — OTP not sent.")
        return False
    try:
        subjects = {
            "login": "FRC System — Login OTP",
            "reset": "FRC System — Password Reset",
        }
        msg = MIMEText(
            f"Your FRC System OTP: {otp_code}\n"
            f"Expires in {settings.OTP_EXPIRY_MINUTES} minutes."
        )
        msg["Subject"] = subjects.get(purpose, "FRC System — OTP")
        msg["From"] = settings.SENDER_EMAIL
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        log.error(f"OTP email failed: {e}")
        return False
