from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, get_current_customer
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from app.models.user import User
from app.models.customer import Customer

router = APIRouter(prefix="/payment", tags=["payment"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/{subscription_id}", response_class=HTMLResponse)
async def payment_page(
    request: Request,
    subscription_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    sub = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.vehicle).joinedload(Vehicle.customer),
            joinedload(Subscription.plan),
        )
        .filter(Subscription.id == subscription_id)
        .first()
    )
    if not sub:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "payment/checkout.html", {
        "user": user, "subscription": sub,
    })


@router.post("/{subscription_id}/confirm")
async def confirm_payment(
    request: Request,
    subscription_id: int,
    card_number: str = Form(...),
    card_name: str = Form(...),
    card_expiry: str = Form(...),
    card_cvv: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    sub = db.query(Subscription).get(subscription_id)
    if not sub:
        raise HTTPException(404)
    if sub.status not in ("pending", "active"):
        raise HTTPException(400, "Bu abonelik odeme beklenmiyor.")

    sub.status = "active"
    sub.payment_simulated = True
    sub.payment_date = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(f"/payment/{subscription_id}/success", status_code=302)


@router.get("/{subscription_id}/success", response_class=HTMLResponse)
async def payment_success(
    request: Request,
    subscription_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    sub = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.vehicle).joinedload(Vehicle.customer),
            joinedload(Subscription.plan),
        )
        .filter(Subscription.id == subscription_id)
        .first()
    )
    if not sub:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "payment/success.html", {
        "user": user, "subscription": sub,
    })
