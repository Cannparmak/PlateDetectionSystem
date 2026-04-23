"""
Auth router — staff login/logout ve müşteri portal kayıt/giriş.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_staff_user
from app.models.customer import Customer
from app.models.user import User
from app.services.auth_service import (
    create_customer_token,
    create_staff_token,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


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
        return templates.TemplateResponse(request, "auth/login.html", {
            "error": "E-posta veya sifre yanlis.",
        }, status_code=400)

    # Son giriş zamanını güncelle (başarısız olursa login'i bloklama)
    try:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    token = create_staff_token(user.id)
    redirect_url = "/admin" if user.role == "admin" else "/dashboard/kasiyer"
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
            return templates.TemplateResponse(request, "auth/register.html", {
                "error": "Bu e-posta adresi zaten kayitli.",
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
        return templates.TemplateResponse(request, "auth/musteri_login.html", {
            "error": "E-posta veya sifre yanlis.",
        }, status_code=400)

    if not verify_password(password, customer.portal_password_hash):
        return templates.TemplateResponse(request, "auth/musteri_login.html", {
            "error": "E-posta veya sifre yanlis.",
        }, status_code=400)

    token = create_customer_token(customer.id)
    response = RedirectResponse("/musteri/dashboard", status_code=302)
    response.set_cookie(
        "customer_token", token,
        httponly=True, samesite="lax",
        max_age=24 * 3600,
    )
    return response
