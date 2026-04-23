"""
Auth servisi — JWT token üretme/doğrulama, şifre hash.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_ALGORITHM = "HS256"
_STAFF_TOKEN_EXPIRE_HOURS = 8
_CUSTOMER_TOKEN_EXPIRE_HOURS = 24

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_access_token(subject: int | str, expires_hours: int = _STAFF_TOKEN_EXPIRE_HOURS) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def create_staff_token(user_id: int) -> str:
    return create_access_token(user_id, _STAFF_TOKEN_EXPIRE_HOURS)


def create_customer_token(customer_id: int) -> str:
    return create_access_token(customer_id, _CUSTOMER_TOKEN_EXPIRE_HOURS)
