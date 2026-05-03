from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_staff_user, require_admin
from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.vehicle import Vehicle
from app.models.user import User
from app.services.auth_service import hash_password
from src.postprocess.text_cleaner import PlateCleaner

_cleaner = PlateCleaner()

router = APIRouter(prefix="/customers", tags=["customers"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


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


def _validate_tc(tc: str) -> tuple[bool, str]:
    """
    TC kimlik no format kontrolü (11 rakam, 0 ile başlamaz).
    Checksum doğrulaması yapılmaz.
    Returns: (geçerli_mi, hata_mesajı)
    """
    tc = tc.strip()
    digits_only = re.sub(r"\D", "", tc)
    if len(digits_only) != 11:
        return False, f"T.C. Kimlik No tam 11 rakam olmalıdır (girilen: {len(digits_only)} rakam)."
    if digits_only[0] == "0":
        return False, "T.C. Kimlik No 0 ile başlayamaz."
    return True, ""


def _normalize_plate(raw: str) -> str:
    """Plakayı normalize et — büyük harf, boşluksuz."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


# ---------------------------------------------------------------------------
# Liste
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def customer_list(
    request: Request,
    search: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    q = db.query(Customer).filter(Customer.is_active == True).options(joinedload(Customer.vehicles))
    if search:
        q = q.filter(
            (Customer.first_name.ilike(f"%{search}%")) |
            (Customer.last_name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
    customers = q.order_by(Customer.created_at.desc()).all()
    return templates.TemplateResponse(request, "customers/list.html", {
        "user": user,
        "customers": customers,
        "search": search,
        "phone_country_code": settings.PHONE_COUNTRY_CODE,
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
    tc_no: str = Form(...),
    plate_number: str = Form(...),
    email: str = Form(default=""),
    address: str = Form(default=""),
    notes: str = Form(default=""),
    portal_password: str = Form(default=""),
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
                "tc_no": tc_no, "plate_number": plate_number,
                "email": email, "address": address, "notes": notes,
            },
        }, status_code=400)

    # TC kontrolü
    tc_ok, tc_err = _validate_tc(tc_no.strip())
    if not tc_ok:
        return _err(tc_err)

    # Telefon doğrulama + normalize
    normalized_phone, phone_err = _build_phone(phone_code, phone.strip())
    if phone_err:
        return _err(phone_err)

    # Plaka kontrolü
    plate = _normalize_plate(plate_number)
    if len(plate) < 5:
        return _err("Geçersiz plaka formatı.")
    existing_plate = db.query(Vehicle).filter(Vehicle.plate_number == plate, Vehicle.is_active == True).first()
    if existing_plate:
        return _err(f"{plate} plakası zaten kayıtlı.")

    # E-posta benzersizlik kontrolü
    if email:
        if db.query(Customer).filter(Customer.email == email.strip().lower()).first():
            return _err("Bu e-posta adresi zaten kayıtlı.")

    customer = Customer(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone=normalized_phone,
        tc_no=tc_no.strip(),
        email=email.strip().lower() or None,
        address=address.strip() or None,
        notes=notes.strip() or None,
        portal_password_hash=hash_password(portal_password) if portal_password else None,
    )
    db.add(customer)
    db.flush()  # customer.id için

    vehicle = Vehicle(
        customer_id=customer.id,
        plate_number=plate,
        plate_display=_cleaner.to_display(plate),
        vehicle_type="otomobil",
    )
    db.add(vehicle)
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
    tc_no: str = Form(...),
    email: str = Form(default=""),
    address: str = Form(default=""),
    notes: str = Form(default=""),
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

    tc_ok, tc_err = _validate_tc(tc_no.strip())
    if not tc_ok:
        return _err(tc_err)

    normalized_phone, phone_err = _build_phone(phone_code, phone.strip())
    if phone_err:
        return _err(phone_err)

    customer.first_name = first_name.strip()
    customer.last_name = last_name.strip()
    customer.phone = normalized_phone
    customer.tc_no = tc_no.strip()
    customer.email = email.strip().lower() or None
    customer.address = address.strip() or None
    customer.notes = notes.strip() or None
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
