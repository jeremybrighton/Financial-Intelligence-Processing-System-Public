"""
FRC System — Security Utilities
JWT, password hashing, API key generation, OTP helpers.
"""

import hashlib, hmac, logging, secrets, smtplib, string, random
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.core.config import settings

log = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta=None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def decode_token_safe(token: str) -> Optional[dict]:
    try:
        return decode_token(token)
    except JWTError:
        return None


def generate_api_key() -> str:
    alphabet = string.ascii_letters + string.digits
    raw = "".join(secrets.choice(alphabet) for _ in range(settings.API_KEY_LENGTH))
    return f"frc_{raw}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), stored_hash)


def get_key_prefix(raw_key: str) -> str:
    return raw_key[-6:]


def generate_otp(length: int = 6) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def send_otp_email(to_email: str, otp_code: str, purpose: str = "login") -> bool:
    if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD:
        log.warning("SMTP credentials not configured — OTP not sent.")
        return False
    try:
        subject_map = {"login": "FRC System — Your Login OTP", "reset": "FRC System — Password Reset OTP"}
        msg = MIMEText(f"Your FRC System OTP: {otp_code}\nExpires in {settings.OTP_EXPIRY_MINUTES} minutes.")
        msg["Subject"] = subject_map.get(purpose, "FRC System — OTP")
        msg["From"] = settings.SENDER_EMAIL
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        log.error(f"Failed to send OTP: {e}")
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
