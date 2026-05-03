"""
FastAPI dependency'leri — auth, DB session, yetki kontrolleri.

Kullanım:
    @router.get("/admin")
    def admin_page(user = Depends(require_admin)):
        ...
"""

from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.customer import Customer
from app.models.user import User

_ALGORITHM = "HS256"


# ------------------------------------------------------------------
# Token decode
# ------------------------------------------------------------------

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum suresi dolmus veya gecersiz token.",
        )


# ------------------------------------------------------------------
# Staff (Admin)
# ------------------------------------------------------------------

def get_current_staff_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Admin kullanıcısı doğrulama."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giris yapmaniz gerekiyor.",
        )
    payload = _decode_token(access_token)
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token.")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici bulunamadi.")
    return user


def require_admin(user: User = Depends(get_current_staff_user)) -> User:
    """Admin yetkisi gerektirir (tüm staff zaten admin)."""
    return user


# ------------------------------------------------------------------
# Müşteri portal
# ------------------------------------------------------------------

def get_current_customer(
    customer_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Customer:
    """Müşteri portal girişi."""
    if not customer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Musteri girisi gereklidir.",
        )
    payload = _decode_token(customer_token)
    customer_id: int | None = payload.get("sub")
    if customer_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token.")

    customer = db.query(Customer).filter(
        Customer.id == int(customer_id),
        Customer.is_active == True,
    ).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Musteri bulunamadi.")
    return customer


# ------------------------------------------------------------------
# Opsiyonel auth (giriş yapılmamış olabilir)
# ------------------------------------------------------------------

def get_optional_staff_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Giriş yapılmamışsa None döner, exception atmaz."""
    if not access_token:
        return None
    try:
        return get_current_staff_user(access_token, db)
    except HTTPException:
        return None
