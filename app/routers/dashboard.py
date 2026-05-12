from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, get_current_customer
from app.i18n import get_templates
from app.models.customer import Customer
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from app.models.user import User
from src.postprocess.text_cleaner import PlateCleaner

router = APIRouter(tags=["dashboard"])
templates = get_templates(Path(__file__).parent.parent / "templates")
_cleaner = PlateCleaner()


@router.get("/dashboard")
async def dashboard_redirect(user: User = Depends(get_current_staff_user)):
    return RedirectResponse("/admin", status_code=302)


@router.get("/musteri/dashboard", response_class=HTMLResponse)
async def musteri_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
    vehicle_error: str = "",
):
    vehicles = (
        db.query(Vehicle)
        .options(joinedload(Vehicle.subscriptions).joinedload(Subscription.plan))
        .filter(Vehicle.customer_id == customer.id, Vehicle.is_active == True)
        .all()
    )

    vehicle_debts: dict[int, float] = {}
    for v in vehicles:
        rows = (
            db.query(ParkingSession.fee_amount)
            .filter(
                ParkingSession.vehicle_id == v.id,
                ParkingSession.is_guest == True,
                ParkingSession.is_paid == False,
                ParkingSession.fee_amount.isnot(None),
                ParkingSession.is_active == False,
            )
            .all()
        )
        vehicle_debts[v.id] = round(sum(r[0] for r in rows if r[0]), 2)

    return templates.TemplateResponse(request, "dashboard/musteri.html", {
        "customer": customer,
        "vehicles": vehicles,
        "vehicle_debts": vehicle_debts,
        "vehicle_error": vehicle_error,
    })


@router.post("/musteri/vehicles/add")
async def musteri_add_vehicle(
    request: Request,
    plate_display: str = Form(...),
    vehicle_type: str = Form(default="otomobil"),
    brand: str = Form(default=""),
    model: str = Form(default=""),
    color: str = Form(default=""),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    plate_number = _cleaner.clean(plate_display)
    valid, fmt = _cleaner.validate(plate_number)
    if not plate_number or not valid or fmt != "TR":
        return RedirectResponse(
            "/musteri/dashboard?vehicle_error=Geçersiz+Türk+plakası.+Beklenen+format%3A+34+ABC+1234",
            status_code=302,
        )

    exists = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    if exists:
        return RedirectResponse(
            f"/musteri/dashboard?vehicle_error={plate_display.strip()}+plakası+zaten+sistemde+kayıtlı",
            status_code=302,
        )

    vehicle = Vehicle(
        customer_id=customer.id,
        plate_number=plate_number,
        plate_display=_cleaner.to_display(plate_number),
        vehicle_type=vehicle_type,
        brand=brand.strip() or None,
        model=model.strip() or None,
        color=color.strip() or None,
    )
    db.add(vehicle)
    db.commit()
    return RedirectResponse("/musteri/dashboard", status_code=302)


@router.post("/musteri/vehicles/{vehicle_id}/remove")
async def musteri_remove_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.customer_id == customer.id,
        Vehicle.is_active == True,
    ).first()
    if not vehicle:
        return RedirectResponse("/musteri/dashboard", status_code=302)

    # Aktif oturumu varsa silme
    active_session = db.query(ParkingSession).filter(
        ParkingSession.vehicle_id == vehicle_id,
        ParkingSession.is_active == True,
    ).first()
    if active_session:
        return RedirectResponse(
            "/musteri/dashboard?vehicle_error=Araç+şu+anda+otoparkta%2C+çıkış+yapılmadan+silinemez",
            status_code=302,
        )

    vehicle.is_active = False
    db.commit()
    return RedirectResponse("/musteri/dashboard", status_code=302)
