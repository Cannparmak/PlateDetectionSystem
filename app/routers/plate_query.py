"""Plaka borç sorgulama — giriş gerektirmez."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from app.services.fee_calculator import FeeCalculator
from app.services.plate_checker import PlateChecker
from src.postprocess.text_cleaner import PlateCleaner

router = APIRouter(tags=["plate_query"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
_cleaner = PlateCleaner()


@router.get("/plaka-sorgula", response_class=HTMLResponse)
async def plate_query_page(
    request: Request,
    plaka: str = "",
    db: Session = Depends(get_db),
):
    """Plaka borç / durum sorgulama sayfası — kimlik doğrulama gerekmez."""
    if not plaka.strip():
        return templates.TemplateResponse(request, "plaka_sorgula.html", {"query": ""})

    plate_input = plaka.strip().upper()
    normalized = _cleaner.clean(plate_input)

    checker = PlateChecker(db)
    vehicle, fuzzy_match, fuzzy_original = checker._resolve_vehicle(normalized)

    if vehicle is None:
        return templates.TemplateResponse(request, "plaka_sorgula.html", {
            "query": plate_input,
            "not_found": True,
        })

    now = datetime.utcnow()

    active_session = (
        db.query(ParkingSession)
        .filter(ParkingSession.vehicle_id == vehicle.id, ParkingSession.is_active == True)
        .first()
    )

    subscription = (
        db.query(Subscription)
        .options(joinedload(Subscription.plan))
        .filter(
            Subscription.vehicle_id == vehicle.id,
            Subscription.status == "active",
            Subscription.end_date > now,
        )
        .order_by(Subscription.end_date.desc())
        .first()
    )

    unpaid_sessions = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.vehicle_id == vehicle.id,
            ParkingSession.is_guest == True,
            ParkingSession.is_paid == False,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.is_active == False,
        )
        .order_by(ParkingSession.exit_time.desc())
        .all()
    )

    total_debt = round(sum(s.fee_amount for s in unpaid_sessions if s.fee_amount), 2)

    estimated_fee = None
    elapsed_minutes = None
    if active_session and active_session.is_guest:
        delta = now - active_session.entry_time
        elapsed_minutes = max(1, int(delta.total_seconds() / 60))
        calc = FeeCalculator(db)
        estimated_fee = calc.calculate(elapsed_minutes)

    return templates.TemplateResponse(request, "plaka_sorgula.html", {
        "query": plate_input,
        "plate_display": vehicle.plate_display,
        "vehicle": vehicle,
        "fuzzy_match": fuzzy_match,
        "fuzzy_original": fuzzy_original,
        "active_session": active_session,
        "subscription": subscription,
        "unpaid_sessions": unpaid_sessions,
        "total_debt": total_debt,
        "estimated_fee": estimated_fee,
        "elapsed_minutes": elapsed_minutes,
    })


def _get_unpaid(plate_number: str, db: Session):
    """Resolve vehicle by plate_number and return (vehicle, unpaid_sessions, total_debt)."""
    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    if vehicle is None:
        return None, [], 0.0
    sessions = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.vehicle_id == vehicle.id,
            ParkingSession.is_guest == True,
            ParkingSession.is_paid == False,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.is_active == False,
        )
        .all()
    )
    total = round(sum(s.fee_amount for s in sessions if s.fee_amount), 2)
    return vehicle, sessions, total


@router.get("/plaka-sorgula/odeme/{plate_number}", response_class=HTMLResponse)
async def payment_page(request: Request, plate_number: str, db: Session = Depends(get_db)):
    vehicle, sessions, total_debt = _get_unpaid(plate_number, db)
    if vehicle is None or total_debt == 0:
        return RedirectResponse(f"/plaka-sorgula?plaka={plate_number}", status_code=303)
    return templates.TemplateResponse(request, "plaka_odeme.html", {
        "plate_number": plate_number,
        "plate_display": vehicle.plate_display,
        "unpaid_sessions": sessions,
        "total_debt": total_debt,
    })


@router.post("/plaka-sorgula/odeme/{plate_number}/confirm", response_class=HTMLResponse)
async def payment_confirm(
    request: Request,
    plate_number: str,
    card_name: str = Form(...),
    card_number: str = Form(...),
    card_expiry: str = Form(...),
    card_cvv: str = Form(...),
    db: Session = Depends(get_db),
):
    vehicle, sessions, total_debt = _get_unpaid(plate_number, db)
    if vehicle is None or total_debt == 0:
        return RedirectResponse(f"/plaka-sorgula?plaka={plate_number}", status_code=303)

    now = datetime.utcnow()
    for s in sessions:
        s.is_paid = True
        s.payment_method = "online"
        s.paid_at = now
    db.commit()

    return RedirectResponse(
        f"/plaka-sorgula/odeme/{plate_number}/basarili?tutar={total_debt:.0f}",
        status_code=303,
    )


@router.get("/plaka-sorgula/odeme/{plate_number}/basarili", response_class=HTMLResponse)
async def payment_success(
    request: Request,
    plate_number: str,
    tutar: str = "0",
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    plate_display = vehicle.plate_display if vehicle else plate_number
    return templates.TemplateResponse(request, "plaka_odeme_basarili.html", {
        "plate_number": plate_number,
        "plate_display": plate_display,
        "tutar": tutar,
    })
