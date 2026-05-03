from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, require_admin
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.user import User
from src.postprocess.text_cleaner import PlateCleaner

router = APIRouter(prefix="/vehicles", tags=["vehicles"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
_cleaner = PlateCleaner()


@router.get("", response_class=HTMLResponse)
async def vehicle_list(
    request: Request,
    search: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    q = db.query(Vehicle).options(joinedload(Vehicle.customer))
    if search:
        plate_search = _cleaner.clean(search)
        q = q.filter(
            Vehicle.plate_number.ilike(f"%{plate_search}%") |
            Vehicle.plate_display.ilike(f"%{search}%")
        )
    vehicles = q.order_by(Vehicle.created_at.desc()).all()
    return templates.TemplateResponse(request, "vehicles/list.html", {
        "user": user,
        "vehicles": vehicles, "search": search,
    })


@router.get("/new", response_class=HTMLResponse)
async def new_vehicle_form(
    request: Request,
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.last_name).all()
    return templates.TemplateResponse(request, "vehicles/form.html", {
        "user": user,
        "vehicle": None, "customers": customers,
        "selected_customer_id": customer_id, "error": None,
    })


@router.post("/new")
async def create_vehicle(
    request: Request,
    customer_id: int = Form(...),
    plate_display: str = Form(...),
    vehicle_type: str = Form(default="otomobil"),
    brand: str = Form(default=""),
    model: str = Form(default=""),
    color: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    plate_number = _cleaner.clean(plate_display)
    valid, fmt = _cleaner.validate(plate_number)
    if not plate_number or not valid or fmt != "TR":
        customers = db.query(Customer).filter(Customer.is_active == True).all()
        return templates.TemplateResponse(request, "vehicles/form.html", {
            "user": user,
            "vehicle": None, "customers": customers,
            "selected_customer_id": customer_id,
            "error": "Gecersiz Turk plakasi. Beklenen format: 34ABC1234 (il kodu 01-81, 1-3 harf, 2-4 rakam).",
        }, status_code=400)

    exists = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    if exists:
        customers = db.query(Customer).filter(Customer.is_active == True).all()
        return templates.TemplateResponse(request, "vehicles/form.html", {
            "user": user,
            "vehicle": None, "customers": customers,
            "selected_customer_id": customer_id,
            "error": f"{plate_number} plakasi zaten kayitli.",
        }, status_code=400)

    vehicle = Vehicle(
        customer_id=customer_id,
        plate_number=plate_number,
        plate_display=_cleaner.to_display(plate_number),
        vehicle_type=vehicle_type,
        brand=brand.strip() or None,
        model=model.strip() or None,
        color=color.strip() or None,
    )
    db.add(vehicle)
    db.commit()
    return RedirectResponse(f"/customers/{customer_id}", status_code=302)


@router.get("/{vehicle_id}/edit", response_class=HTMLResponse)
async def edit_vehicle_form(
    request: Request,
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    vehicle = db.query(Vehicle).options(joinedload(Vehicle.customer)).get(vehicle_id)
    if not vehicle:
        raise HTTPException(404)
    customers = db.query(Customer).filter(Customer.is_active == True).order_by(Customer.last_name).all()
    return templates.TemplateResponse(request, "vehicles/form.html", {
        "user": user,
        "vehicle": vehicle,
        "customers": customers,
        "selected_customer_id": vehicle.customer_id,
        "error": None,
    })


@router.post("/{vehicle_id}/edit")
async def update_vehicle(
    request: Request,
    vehicle_id: int,
    plate_display: str = Form(...),
    vehicle_type: str = Form(default="otomobil"),
    brand: str = Form(default=""),
    model: str = Form(default=""),
    color: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    if not vehicle:
        raise HTTPException(404)

    plate_number = _cleaner.clean(plate_display)
    valid, fmt = _cleaner.validate(plate_number)
    if not plate_number or not valid or fmt != "TR":
        raise HTTPException(400, "Gecersiz Turk plakasi. Beklenen format: 34ABC1234 (il kodu 01-81, 1-3 harf, 2-4 rakam).")

    # Check duplicate (ignore self)
    exists = db.query(Vehicle).filter(
        Vehicle.plate_number == plate_number,
        Vehicle.id != vehicle_id
    ).first()
    if exists:
        raise HTTPException(400, f"{plate_number} plakasi baska bir aracta kayitli.")

    vehicle.plate_display = _cleaner.to_display(plate_number)
    vehicle.plate_number  = plate_number
    vehicle.vehicle_type  = vehicle_type
    vehicle.brand  = brand.strip() or None
    vehicle.model  = model.strip() or None
    vehicle.color  = color.strip() or None
    db.commit()
    return RedirectResponse(f"/customers/{vehicle.customer_id}", status_code=302)


@router.post("/{vehicle_id}/delete")
async def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    if not vehicle:
        raise HTTPException(404)
    customer_id = vehicle.customer_id
    vehicle.is_active = False
    db.commit()
    return RedirectResponse(f"/customers/{customer_id}", status_code=302)
