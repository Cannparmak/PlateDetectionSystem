from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, get_current_customer
from app.models.customer import Customer
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from app.models.user import User

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/dashboard")
async def dashboard_redirect(user: User = Depends(get_current_staff_user)):
    if user.role == "admin":
        return RedirectResponse("/admin", status_code=302)
    return RedirectResponse("/dashboard/kasiyer", status_code=302)


@router.get("/dashboard/kasiyer", response_class=HTMLResponse)
async def kasiyer_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    from datetime import datetime
    now = datetime.utcnow()
    active_sessions = (
        db.query(ParkingSession)
        .options(joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer))
        .filter(ParkingSession.is_active == True)
        .order_by(ParkingSession.entry_time.desc())
        .all()
    )
    from app.models.parking_config import ParkingConfig
    config = db.query(ParkingConfig).first()
    capacity = config.total_capacity if config else 100

    return templates.TemplateResponse(request, "dashboard/kasiyer.html", {
        "user": user,
        "active_sessions": active_sessions,
        "active_count": len(active_sessions),
        "capacity": capacity,
    })


@router.get("/musteri/dashboard", response_class=HTMLResponse)
async def musteri_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    from datetime import datetime
    vehicles = (
        db.query(Vehicle)
        .options(joinedload(Vehicle.subscriptions).joinedload(Subscription.plan))
        .filter(Vehicle.customer_id == customer.id, Vehicle.is_active == True)
        .all()
    )
    return templates.TemplateResponse(request, "dashboard/musteri.html", {
        "customer": customer,
        "vehicles": vehicles,
    })
