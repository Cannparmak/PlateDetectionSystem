from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, get_current_customer
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from app.models.user import User

router = APIRouter(tags=["subscriptions"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/subscriptions/plans", response_class=HTMLResponse)
async def plans_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.display_order).all()
    return templates.TemplateResponse(request, "subscriptions/plans.html", {
        "user": user, "plans": plans,
    })


@router.get("/subscriptions/new", response_class=HTMLResponse)
async def new_subscription_form(
    request: Request,
    vehicle_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.display_order).all()
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).get(vehicle_id) if vehicle_id else None
    return templates.TemplateResponse(request, "subscriptions/new.html", {
        "user": user,
        "plans": plans, "vehicle": vehicle, "error": None,
    })


@router.post("/subscriptions/new")
async def create_subscription(
    request: Request,
    vehicle_id: int = Form(...),
    plan_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    plan = db.query(SubscriptionPlan).get(plan_id)
    if not vehicle or not plan:
        raise HTTPException(404)

    # Mevcut aktif aboneliği sonlandır
    existing = db.query(Subscription).filter(
        Subscription.vehicle_id == vehicle_id,
        Subscription.status == "active",
        Subscription.end_date > datetime.utcnow(),
    ).first()
    if existing:
        existing.status = "cancelled"

    now = datetime.utcnow()
    sub = Subscription(
        vehicle_id=vehicle_id,
        plan_id=plan_id,
        start_date=now,
        end_date=now + timedelta(hours=plan.duration_hours),
        status="pending",
        total_paid=plan.price,
        created_by_user_id=user.id,
    )
    db.add(sub)
    db.commit()

    return RedirectResponse(f"/payment/{sub.id}", status_code=302)


@router.get("/subscriptions", response_class=HTMLResponse)
async def subscription_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    subs = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.vehicle).joinedload(Vehicle.customer),
            joinedload(Subscription.plan),
        )
        .order_by(Subscription.created_at.desc())
        .limit(200)
        .all()
    )
    return templates.TemplateResponse(request, "subscriptions/list.html", {
        "user": user, "subscriptions": subs,
    })


@router.get("/musteri/subscriptions", response_class=HTMLResponse)
async def musteri_subscriptions(
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
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.display_order).all()

    return templates.TemplateResponse(request, "subscriptions/musteri_list.html", {
        "customer": customer,
        "vehicles": vehicles, "plans": plans,
    })
