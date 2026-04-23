from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, require_admin
from app.models.customer import Customer
from app.models.parking_config import ParkingConfig
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.auth_service import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "total_customers": db.query(Customer).filter(Customer.is_active == True).count(),
        "total_vehicles": db.query(Vehicle).filter(Vehicle.is_active == True).count(),
        "active_subscriptions": db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date > now,
        ).count(),
        "active_sessions": db.query(ParkingSession).filter(ParkingSession.is_active == True).count(),
        "today_entries": db.query(ParkingSession).filter(
            ParkingSession.entry_time >= today_start
        ).count(),
        "expiring_soon": db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.end_date > now,
            Subscription.end_date <= now + timedelta(days=3),
        ).count(),
    }

    config = db.query(ParkingConfig).first()
    recent_sessions = (
        db.query(ParkingSession)
        .options(joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer))
        .order_by(ParkingSession.entry_time.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "user": user,
        "stats": stats, "config": config,
        "recent_sessions": recent_sessions,
    })


@router.get("/users", response_class=HTMLResponse)
async def user_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at).all()
    return templates.TemplateResponse(request, "admin/users.html", {
        "user": user, "users": users,
    })


@router.post("/users/new")
async def create_user(
    email: str = Form(...),
    username: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == email.strip().lower()).first():
        raise HTTPException(400, "Bu e-posta zaten kayitli.")
    new_user = User(
        email=email.strip().lower(),
        username=username.strip(),
        full_name=full_name.strip(),
        role=role,
        hashed_password=hash_password(password),
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.post("/users/{user_id}/toggle")
async def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    u = db.query(User).get(user_id)
    if not u or u.id == current_user.id:
        raise HTTPException(400)
    u.is_active = not u.is_active
    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


@router.get("/reports", response_class=HTMLResponse)
async def reports(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    from datetime import datetime, timedelta
    now = datetime.utcnow()

    daily_entries = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = db.query(ParkingSession).filter(
            ParkingSession.entry_time >= day_start,
            ParkingSession.entry_time <= day_end,
        ).count()
        daily_entries.append({"date": day.strftime("%d.%m"), "count": count})

    plan_stats = []
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    for plan in plans:
        count = db.query(Subscription).filter(
            Subscription.plan_id == plan.id,
            Subscription.status == "active",
        ).count()
        plan_stats.append({"name": plan.name, "count": count})

    return templates.TemplateResponse(request, "admin/reports.html", {
        "user": user,
        "daily_entries": daily_entries,
        "plan_stats": plan_stats,
    })


@router.post("/config")
async def update_config(
    name: str = Form(...),
    address: str = Form(default=""),
    phone: str = Form(default=""),
    total_capacity: int = Form(...),
    open_time: str = Form(default="00:00"),
    close_time: str = Form(default="23:59"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    config = db.query(ParkingConfig).first()
    if not config:
        config = ParkingConfig()
        db.add(config)

    config.name = name.strip()
    config.address = address.strip() or None
    config.phone = phone.strip() or None
    config.total_capacity = total_capacity
    config.open_time = open_time
    config.close_time = close_time
    db.commit()
    return RedirectResponse("/admin", status_code=302)
