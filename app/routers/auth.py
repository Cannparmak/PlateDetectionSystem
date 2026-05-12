"""
Auth router — staff login/logout ve müşteri portal kayıt/giriş.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_staff_user
from app.i18n import get_request_lang, get_templates, translate
from app.models.customer import Customer
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.auth_service import (
    create_customer_token,
    create_staff_token,
    hash_password,
    verify_password,
)
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
templates = get_templates(Path(__file__).parent.parent / "templates")


# ------------------------------------------------------------------
# Staff — Login / Logout
# ------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(get_optional_staff_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "auth/login.html", {
        "error": None,
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == email.strip().lower(),
        User.is_active == True,
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        lang = get_request_lang(request)
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": translate("auth.invalid_credentials", lang),
        }, status_code=400)

    # Son giriş zamanını güncelle (başarısız olursa login'i bloklama)
    try:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    token = create_staff_token(user.id)
    redirect_url = "/admin"
    response = RedirectResponse(redirect_url, status_code=302)
    response.set_cookie(
        "access_token", token,
        httponly=True, samesite="lax",
        max_age=8 * 3600,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    response.delete_cookie("customer_token")
    return response


# ------------------------------------------------------------------
# Müşteri Portal — Kayıt
# ------------------------------------------------------------------

@router.get("/musteri/register", response_class=HTMLResponse)
async def musteri_register_page(request: Request):
    return templates.TemplateResponse(request, "auth/register.html", {
        "error": None,
    })


@router.post("/musteri/register")
async def musteri_register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(default=""),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # E-posta benzersizlik kontrolü
    if email:
        exists = db.query(Customer).filter(Customer.email == email.strip().lower()).first()
        if exists:
            lang = get_request_lang(request)
            return templates.TemplateResponse(request, "auth/register.html", {
                "error": translate("auth.email_exists", lang),
            }, status_code=400)

    customer = Customer(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=phone.strip(),
        email=email.strip().lower() or None,
        portal_password_hash=hash_password(password),
    )
    db.add(customer)
    db.commit()

    token = create_customer_token(customer.id)
    response = RedirectResponse("/musteri/dashboard", status_code=302)
    response.set_cookie(
        "customer_token", token,
        httponly=True, samesite="lax",
        max_age=24 * 3600,
    )
    return response


# ------------------------------------------------------------------
# Müşteri Portal — Giriş
# ------------------------------------------------------------------

@router.get("/musteri/login", response_class=HTMLResponse)
async def musteri_login_page(request: Request):
    return templates.TemplateResponse(request, "auth/musteri_login.html", {
        "error": None,
    })


@router.post("/musteri/login")
async def musteri_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower(),
        Customer.is_active == True,
    ).first()

    if not customer or not customer.portal_password_hash:
        lang = get_request_lang(request)
        return templates.TemplateResponse(request, "auth/musteri_login.html", {
            "error": translate("auth.invalid_credentials", lang),
        }, status_code=400)

    if not verify_password(password, customer.portal_password_hash):
        lang = get_request_lang(request)
        return templates.TemplateResponse(request, "auth/musteri_login.html", {
            "error": translate("auth.invalid_credentials", lang),
        }, status_code=400)

    token = create_customer_token(customer.id)
    response = RedirectResponse("/musteri/dashboard", status_code=302)
    response.set_cookie(
        "customer_token", token,
        httponly=True, samesite="lax",
        max_age=24 * 3600,
    )
    return response


# ------------------------------------------------------------------
# Yardımcı — Reset token oluştur
# ------------------------------------------------------------------

def _create_reset_token(db: Session, user_type: str, user_id: int) -> str:
    # Eski kullanılmamış token varsa geçersiz kıl
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_type == user_type,
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    raw = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db_token = PasswordResetToken(
        token=raw,
        user_type=user_type,
        user_id=user_id,
        expires_at=expires,
    )
    db.add(db_token)
    db.commit()
    return raw


# ------------------------------------------------------------------
# Staff — Şifremi Unuttum
# ------------------------------------------------------------------

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "auth/forgot_password.html", {
        "sent": False,
        "error": None,
        "user_type": "staff",
    })


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    lang = get_request_lang(request)
    user = db.query(User).filter(
        User.email == email.strip().lower(),
        User.is_active == True,
    ).first()

    # Güvenlik: kullanıcı bulunamasa bile aynı mesajı göster
    if user:
        raw = _create_reset_token(db, "staff", user.id)
        base_url = str(request.base_url).rstrip("/")
        reset_link = f"{base_url}/reset-password/{raw}"
        try:
            await send_password_reset_email(
                to_email=user.email,
                reset_link=reset_link,
                user_name=user.full_name if hasattr(user, "full_name") else user.email,
                is_staff=True,
            )
        except Exception:
            logger.exception("Şifre sıfırlama maili gönderilemedi")

    return templates.TemplateResponse(request, "auth/forgot_password.html", {
        "sent": True,
        "error": None,
        "user_type": "staff",
    })


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(token: str, request: Request, db: Session = Depends(get_db)):
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.user_type == "staff",
        PasswordResetToken.used == False,
    ).first()

    expired = False
    if db_token:
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expired = expires_at < datetime.now(timezone.utc)

    return templates.TemplateResponse(request, "auth/reset_password.html", {
        "token": token,
        "valid": db_token is not None and not expired,
        "expired": expired,
        "success": False,
        "error": None,
        "user_type": "staff",
    })


@router.post("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password(
    token: str,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    lang = get_request_lang(request)
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.user_type == "staff",
        PasswordResetToken.used == False,
    ).first()

    if not db_token:
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": False,
            "success": False, "error": "Geçersiz bağlantı.", "user_type": "staff",
        }, status_code=400)

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": True,
            "success": False, "error": None, "user_type": "staff",
        }, status_code=400)

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": False,
            "success": False, "error": "Kullanıcı bulunamadı.", "user_type": "staff",
        }, status_code=400)

    user.hashed_password = hash_password(password)
    db_token.used = True
    db.commit()

    return templates.TemplateResponse(request, "auth/reset_password.html", {
        "token": token, "valid": True, "expired": False,
        "success": True, "error": None, "user_type": "staff",
    })


# ------------------------------------------------------------------
# Müşteri — Şifremi Unuttum
# ------------------------------------------------------------------

@router.get("/musteri/forgot-password", response_class=HTMLResponse)
async def musteri_forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "auth/forgot_password.html", {
        "sent": False,
        "error": None,
        "user_type": "customer",
    })


@router.post("/musteri/forgot-password", response_class=HTMLResponse)
async def musteri_forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(
        Customer.email == email.strip().lower(),
        Customer.is_active == True,
    ).first()

    if customer and customer.portal_password_hash:
        raw = _create_reset_token(db, "customer", customer.id)
        base_url = str(request.base_url).rstrip("/")
        reset_link = f"{base_url}/musteri/reset-password/{raw}"
        try:
            await send_password_reset_email(
                to_email=customer.email,
                reset_link=reset_link,
                user_name=f"{customer.first_name} {customer.last_name}",
                is_staff=False,
            )
        except Exception:
            logger.exception("Müşteri şifre sıfırlama maili gönderilemedi")

    return templates.TemplateResponse(request, "auth/forgot_password.html", {
        "sent": True,
        "error": None,
        "user_type": "customer",
    })


@router.get("/musteri/reset-password/{token}", response_class=HTMLResponse)
async def musteri_reset_password_page(token: str, request: Request, db: Session = Depends(get_db)):
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.user_type == "customer",
        PasswordResetToken.used == False,
    ).first()

    expired = False
    if db_token:
        expires_at = db_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expired = expires_at < datetime.now(timezone.utc)

    return templates.TemplateResponse(request, "auth/reset_password.html", {
        "token": token,
        "valid": db_token is not None and not expired,
        "expired": expired,
        "success": False,
        "error": None,
        "user_type": "customer",
    })


@router.post("/musteri/reset-password/{token}", response_class=HTMLResponse)
async def musteri_reset_password(
    token: str,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.user_type == "customer",
        PasswordResetToken.used == False,
    ).first()

    if not db_token:
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": False,
            "success": False, "error": "Geçersiz bağlantı.", "user_type": "customer",
        }, status_code=400)

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": True,
            "success": False, "error": None, "user_type": "customer",
        }, status_code=400)

    customer = db.query(Customer).filter(Customer.id == db_token.user_id).first()
    if not customer:
        return templates.TemplateResponse(request, "auth/reset_password.html", {
            "token": token, "valid": False, "expired": False,
            "success": False, "error": "Müşteri bulunamadı.", "user_type": "customer",
        }, status_code=400)

    customer.portal_password_hash = hash_password(password)
    db_token.used = True
    db.commit()

    return templates.TemplateResponse(request, "auth/reset_password.html", {
        "token": token, "valid": True, "expired": False,
        "success": True, "error": None, "user_type": "customer",
    })
