from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, get_current_customer
from app.models.customer import Customer
from app.models.parking_session import ParkingSession
from app.models.vehicle import Vehicle
from app.models.user import User

router = APIRouter(tags=["sessions"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/sessions", response_class=HTMLResponse)
async def session_history(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    per_page = 50
    offset = (page - 1) * per_page

    sessions = (
        db.query(ParkingSession)
        .options(
            joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer),
        )
        .order_by(ParkingSession.entry_time.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    total = db.query(ParkingSession).count()
    active_count = db.query(ParkingSession).filter(ParkingSession.is_active == True).count()

    return templates.TemplateResponse(request, "sessions/history.html", {
        "user": user,
        "sessions": sessions,
        "active_count": active_count,
        "total": total, "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@router.get("/musteri/sessions", response_class=HTMLResponse)
async def musteri_session_history(
    request: Request,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    vehicles = db.query(Vehicle).filter(
        Vehicle.customer_id == customer.id
    ).all()
    vehicle_ids = [v.id for v in vehicles]

    sessions = (
        db.query(ParkingSession)
        .options(joinedload(ParkingSession.vehicle))
        .filter(ParkingSession.vehicle_id.in_(vehicle_ids))
        .order_by(ParkingSession.entry_time.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(request, "sessions/musteri_history.html", {
        "customer": customer,
        "sessions": sessions,
    })


# API — anlık doluluk
@router.get("/api/sessions/occupancy")
async def get_occupancy(db: Session = Depends(get_db)):
    from app.models.parking_config import ParkingConfig
    config = db.query(ParkingConfig).first()
    active = db.query(ParkingSession).filter(ParkingSession.is_active == True).count()
    capacity = config.total_capacity if config else 100
    return {
        "active": active,
        "capacity": capacity,
        "available": max(0, capacity - active),
        "occupancy_pct": round(active / capacity * 100, 1) if capacity else 0,
    }


# API — şu an içerideki araçlar
@router.get("/api/sessions/active-vehicles")
async def get_active_vehicles(db: Session = Depends(get_db)):
    """Aktif park oturumlarını (şu an içeride) döndürür."""
    sessions = (
        db.query(ParkingSession)
        .options(
            joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer)
        )
        .filter(ParkingSession.is_active == True)
        .order_by(ParkingSession.entry_time.desc())
        .all()
    )
    return [
        {
            "session_id": s.id,
            "plate": s.vehicle.plate_number if s.vehicle else "?",
            "customer_name": s.vehicle.customer.full_name if s.vehicle and s.vehicle.customer else None,
            "entry_time": s.entry_time.strftime("%H:%M"),
            "entry_date": s.entry_time.strftime("%d.%m"),
        }
        for s in sessions
    ]
