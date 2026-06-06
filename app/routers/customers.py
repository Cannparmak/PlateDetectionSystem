from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_staff_user, require_admin
from app.i18n import get_templates
from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.vehicle import Vehicle
from app.models.user import User
from app.services.auth_service import hash_password

router = APIRouter(prefix="/customers", tags=["customers"])
templates = get_templates(Path(__file__).parent.parent / "templates")


# ---------------------------------------------------------------------------
# Ülke kodları listesi — (kod, etiket) çiftleri
# ---------------------------------------------------------------------------

PHONE_COUNTRY_CODES: list[tuple[str, str]] = [
    ("+90", "Türkiye (+90)"),
    ("+49", "Almanya (+49)"),
    ("+31", "Hollanda (+31)"),
    ("+32", "Belçika (+32)"),
    ("+33", "Fransa (+33)"),
    ("+39", "İtalya (+39)"),
    ("+43", "Avusturya (+43)"),
    ("+44", "Birleşik Krallık (+44)"),
    ("+1",  "ABD / Kanada (+1)"),
]

_CODE_VALUES = [c for c, _ in PHONE_COUNTRY_CODES]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _parse_stored_phone(full_phone: str) -> tuple[str, str]:
    """
    Kayıtlı telefon numarasını kod + yerel parça olarak ayırır.
    "+905321234567" → ("+90", "5321234567")
    Bilinmeyen kod → ("+90", orijinal)
    """
    for code in sorted(_CODE_VALUES, key=len, reverse=True):  # uzundan kısaya
        if full_phone.startswith(code):
            return code, full_phone[len(code):]
    return "+90", full_phone.lstrip("+")


def _build_phone(code: str, local: str) -> tuple[str, str]:
    """
    Seçilen ülke kodu + yerel numara → normalize edilmiş tam numara + hata mesajı.
    Hata yoksa hata mesajı boş string döner.
    """
    code = code.strip() if code in _CODE_VALUES else "+90"
    digits = re.sub(r"\D", "", local)   # sadece rakamlar
    digits = digits.lstrip("0")         # baştaki sıfırları at (0532 → 532)

    if code == "+90":
        if len(digits) != 10:
            return "", "Türkiye (+90) için telefon numarası 10 haneli olmalıdır (örn: 5321234567)."
    else:
        if not (7 <= len(digits) <= 12):
            return "", "Telefon numarası 7 ile 12 hane arasında olmalıdır."

    return f"{code}{digits}", ""


# ---------------------------------------------------------------------------
# Liste
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def customer_list(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    per_page = 10
    q = db.query(Customer).filter(Customer.is_active == True).options(joinedload(Customer.vehicles))
    if search.strip():
        # Her kelime ayrı eşleşmeli: "ahmet durmaz" → first=Ahmet, last=Durmaz
        for token in search.split():
            like = f"%{token}%"
            q = q.filter(
                Customer.first_name.ilike(like) |
                Customer.last_name.ilike(like) |
                Customer.phone.ilike(like) |
                Customer.email.ilike(like)
            )
    total = q.count()
    customers = q.order_by(Customer.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse(request, "customers/list.html", {
        "user": user,
        "customers": customers,
        "search": search,
        "phone_country_code": settings.PHONE_COUNTRY_CODE,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


# ---------------------------------------------------------------------------
# Yeni müşteri
# ---------------------------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
async def new_customer_form(
    request: Request,
    user: User = Depends(get_current_staff_user),
):
    return templates.TemplateResponse(request, "customers/form.html", {
        "user": user,
        "customer": None,
        "error": None,
        "phone_codes": PHONE_COUNTRY_CODES,
        "selected_code": settings.PHONE_COUNTRY_CODE,
        "phone_local": "",
    })


@router.post("/new")
async def create_customer(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_code: str = Form(default="+90"),
    phone: str = Form(...),
    email: str = Form(...),
    portal_password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    def _err(msg: str):
        return templates.TemplateResponse(request, "customers/form.html", {
            "user": user, "customer": None, "error": msg,
            "phone_codes": PHONE_COUNTRY_CODES,
            "selected_code": phone_code,
            "phone_local": phone,
            "form": {
                "first_name": first_name, "last_name": last_name,
                "email": email,
            },
        }, status_code=400)

    # Telefon doğrulama + normalize
    normalized_phone, phone_err = _build_phone(phone_code, phone.strip())
    if phone_err:
        return _err(phone_err)

    # E-posta benzersizlik kontrolü
    if db.query(Customer).filter(Customer.email == email.strip().lower()).first():
        return _err("Bu e-posta adresi zaten kayıtlı.")

    if len(portal_password) < 6:
        return _err("Şifre en az 6 karakter olmalıdır.")

    customer = Customer(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=normalized_phone,
        email=email.strip().lower(),
        portal_password_hash=hash_password(portal_password),
    )
    db.add(customer)
    db.commit()
    return RedirectResponse(f"/customers/{customer.id}", status_code=302)


# ---------------------------------------------------------------------------
# Detay
# ---------------------------------------------------------------------------

@router.get("/{customer_id}", response_class=HTMLResponse)
async def customer_detail(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    customer = (
        db.query(Customer)
        .options(
            joinedload(Customer.vehicles).joinedload(Vehicle.subscriptions).joinedload(Subscription.plan),
            joinedload(Customer.vehicles).joinedload(Vehicle.parking_sessions),
        )
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(404, "Musteri bulunamadi.")
    return templates.TemplateResponse(request, "customers/detail.html", {
        "user": user, "customer": customer,
    })


# ---------------------------------------------------------------------------
# Düzenle
# ---------------------------------------------------------------------------

@router.get("/{customer_id}/edit", response_class=HTMLResponse)
async def edit_customer_form(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404)
    selected_code, phone_local = _parse_stored_phone(customer.phone or "")
    return templates.TemplateResponse(request, "customers/form.html", {
        "user": user,
        "customer": customer,
        "error": None,
        "phone_codes": PHONE_COUNTRY_CODES,
        "selected_code": selected_code,
        "phone_local": phone_local,
    })


@router.post("/{customer_id}/edit")
async def update_customer(
    request: Request,
    customer_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_code: str = Form(default="+90"),
    phone: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404)

    def _err(msg: str):
        return templates.TemplateResponse(request, "customers/form.html", {
            "user": user, "customer": customer, "error": msg,
            "phone_codes": PHONE_COUNTRY_CODES,
            "selected_code": phone_code,
            "phone_local": phone,
        }, status_code=400)

    normalized_phone, phone_err = _build_phone(phone_code, phone.strip())
    if phone_err:
        return _err(phone_err)

    # E-posta benzersizlik kontrolü (başka müşteriye ait olmamalı)
    existing = db.query(Customer).filter(
        Customer.email == email.strip().lower(),
        Customer.id != customer_id,
    ).first()
    if existing:
        return _err("Bu e-posta adresi zaten kayıtlı.")

    customer.first_name = first_name.strip()
    customer.last_name = last_name.strip()
    customer.phone = normalized_phone
    customer.email = email.strip().lower()
    db.commit()
    return RedirectResponse(f"/customers/{customer_id}", status_code=302)


# ---------------------------------------------------------------------------
# Silme (kalıcı — sadece admin)
# ---------------------------------------------------------------------------

@router.post("/{customer_id}/delete")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404)

    # Aktif park oturumu varsa silmeyi engelle
    from app.models.parking_session import ParkingSession
    active_sessions = (
        db.query(ParkingSession)
        .join(Vehicle, ParkingSession.vehicle_id == Vehicle.id)
        .filter(
            Vehicle.customer_id == customer_id,
            ParkingSession.is_active == True,
        )
        .count()
    )
    if active_sessions > 0:
        raise HTTPException(
            400,
            "Bu müşterinin otoparkta aktif aracı var. Önce çıkış yapılmalı."
        )

    db.delete(customer)   # cascade: vehicle → subscription → session
    db.commit()
    return RedirectResponse("/customers", status_code=302)
