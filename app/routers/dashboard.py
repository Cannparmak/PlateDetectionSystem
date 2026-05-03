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
    return RedirectResponse("/admin", status_code=302)


@router.get("/musteri/dashboard", response_class=HTMLResponse)
async def musteri_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
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
    })
