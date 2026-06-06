from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_staff_user, require_admin
from app.i18n import get_request_lang, get_templates, translate
from app.models.customer import Customer
from app.models.parking_config import ParkingConfig
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.parking_rate_bracket import ParkingRateBracket
from app.services.auth_service import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])
templates = get_templates(Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    from datetime import datetime, timedelta
    from sqlalchemy import func as sqlfunc

    now = datetime.utcnow()
    today_start  = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start   = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

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

    def _park_rev(start):
        return db.query(
            sqlfunc.coalesce(sqlfunc.sum(ParkingSession.fee_amount), 0)
        ).filter(
            ParkingSession.is_paid == True,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.paid_at >= start,
        ).scalar() or 0.0

    def _sub_rev(start):
        return db.query(
            sqlfunc.coalesce(sqlfunc.sum(Subscription.total_paid), 0)
        ).filter(
            Subscription.total_paid > 0,
            Subscription.created_at >= start,
        ).scalar() or 0.0

    revenue = {
        "today":  round(_park_rev(today_start) + _sub_rev(today_start), 2),
        "month":  round(_park_rev(month_start) + _sub_rev(month_start), 2),
        "year":   round(_park_rev(year_start)  + _sub_rev(year_start),  2),
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
        "stats": stats,
        "revenue": revenue,
        "config": config,
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
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == email.strip().lower()).first():
        raise HTTPException(400, "Bu e-posta zaten kayitli.")
    # Kasiyer rolü kaldırıldı — tüm personel hesapları admin
    new_user = User(
        email=email.strip().lower(),
        username=username.strip(),
        full_name=full_name.strip(),
        role="admin",
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
    from sqlalchemy import func as sqlfunc

    now         = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start  = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    daily_entries = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day.replace(hour=23, minute=59, second=59)
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

    # ── Hasılat hesapları ──────────────────────────────────────────────
    def _park_rev(start, end=None):
        q = db.query(sqlfunc.coalesce(sqlfunc.sum(ParkingSession.fee_amount), 0)).filter(
            ParkingSession.is_paid == True,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.paid_at >= start,
        )
        if end:
            q = q.filter(ParkingSession.paid_at <= end)
        return float(q.scalar() or 0)

    def _sub_rev(start, end=None):
        q = db.query(sqlfunc.coalesce(sqlfunc.sum(Subscription.total_paid), 0)).filter(
            Subscription.total_paid > 0,
            Subscription.created_at >= start,
        )
        if end:
            q = q.filter(Subscription.created_at <= end)
        return float(q.scalar() or 0)

    park_today  = round(_park_rev(today_start), 2)
    park_month  = round(_park_rev(month_start), 2)
    park_year   = round(_park_rev(year_start),  2)
    sub_today   = round(_sub_rev(today_start),  2)
    sub_month   = round(_sub_rev(month_start),  2)
    sub_year    = round(_sub_rev(year_start),   2)

    revenue = {
        "today":       round(park_today + sub_today, 2),
        "month":       round(park_month + sub_month, 2),
        "year":        round(park_year  + sub_year,  2),
        "park_today":  park_today,
        "park_month":  park_month,
        "park_year":   park_year,
        "sub_today":   sub_today,
        "sub_month":   sub_month,
        "sub_year":    sub_year,
    }

    # Son 30 günlük günlük hasılat (bar chart için)
    daily_revenue = []
    for i in range(29, -1, -1):
        day       = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day.replace(hour=23, minute=59, second=59)
        park = _park_rev(day_start, day_end)
        sub  = _sub_rev(day_start, day_end)
        daily_revenue.append({
            "date":  day.strftime("%d.%m"),
            "total": round(park + sub, 2),
            "park":  park,
            "sub":   sub,
        })

    # Ödeme yöntemi dağılımı (bu ay)
    cash_rev = db.query(sqlfunc.coalesce(sqlfunc.sum(ParkingSession.fee_amount), 0)).filter(
        ParkingSession.is_paid == True,
        ParkingSession.fee_amount.isnot(None),
        ParkingSession.paid_at >= month_start,
        ParkingSession.payment_method == "nakit",
    ).scalar() or 0
    card_rev = db.query(sqlfunc.coalesce(sqlfunc.sum(ParkingSession.fee_amount), 0)).filter(
        ParkingSession.is_paid == True,
        ParkingSession.fee_amount.isnot(None),
        ParkingSession.paid_at >= month_start,
        ParkingSession.payment_method == "kredi_karti",
    ).scalar() or 0

    return templates.TemplateResponse(request, "admin/reports.html", {
        "user": user,
        "daily_entries": daily_entries,
        "plan_stats": plan_stats,
        "revenue": revenue,
        "daily_revenue": daily_revenue,
        "cash_rev": round(float(cash_rev), 2),
        "card_rev": round(float(card_rev), 2),
    })


@router.get("/debts", response_class=HTMLResponse)
async def admin_debts(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Ödenmemiş misafir borçları listesi — içeridekiler dahil."""
    from datetime import datetime as dt
    from app.services.fee_calculator import FeeCalculator

    fee_calc = FeeCalculator(db)
    now = dt.utcnow()

    # Çıkış yapmış, ödenmemiş oturumlar
    exited = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.is_guest == True,
            ParkingSession.is_paid == False,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.is_active == False,
        )
        .options(joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer))
        .all()
    )

    # Hâlâ içerideki misafir araçlar — anlık ücret hesapla (DB'ye yazmadan)
    active_raw = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.is_guest == True,
            ParkingSession.is_active == True,
            ParkingSession.is_paid == False,
        )
        .options(joinedload(ParkingSession.vehicle).joinedload(Vehicle.customer))
        .all()
    )

    # Autoflush'tan kaçınmak için tarayıcıyı ayır, hesapları ayrı dict'te tut
    computed: dict[int, dict] = {}
    db.autoflush = False
    try:
        for s in active_raw:
            duration = max(1, int((now - s.entry_time).total_seconds() / 60))
            fee = fee_calc.calculate(duration)
            computed[s.id] = {"duration_minutes": duration, "fee_amount": fee}
    finally:
        db.autoflush = True

    # Wrapper: template s.fee_amount / s.duration_minutes / s.still_inside ile çalışır
    class _SessionProxy:
        def __init__(self, session: ParkingSession, extra: dict, still_inside: bool):
            self._s = session
            self._extra = extra
            self.still_inside = still_inside

        def __getattr__(self, name: str):
            if name in self._extra:
                return self._extra[name]
            return getattr(self._s, name)

    rows: list = []
    for s in exited:
        rows.append(_SessionProxy(s, {}, still_inside=False))
    for s in active_raw:
        extra = computed[s.id]
        if extra["fee_amount"] > 0:
            rows.append(_SessionProxy(s, extra, still_inside=True))

    rows.sort(key=lambda p: p.fee_amount or 0, reverse=True)

    total_unpaid = round(sum(p.fee_amount for p in rows if p.fee_amount), 2)
    total = len(rows)
    per_page = 10
    sessions = rows[(page - 1) * per_page: page * per_page]

    return templates.TemplateResponse(request, "admin/debts.html", {
        "user": user,
        "sessions": sessions,
        "total_unpaid": total_unpaid,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@router.post("/debts/{session_id}/pay")
async def mark_debt_paid(
    session_id: int,
    payment_method: str = Form(default="nakit"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Seçilen borç oturumunu ödenmiş olarak işaretle."""
    from datetime import datetime as dt
    from app.services.fee_calculator import FeeCalculator

    session = db.query(ParkingSession).get(session_id)
    if not session or not session.is_guest or session.is_paid:
        raise HTTPException(400, "Gecersiz istek.")

    # Araç hâlâ içerideyse anlık ücreti hesapla ve kaydet
    if session.is_active and session.fee_amount is None:
        now = dt.utcnow()
        duration = max(1, int((now - session.entry_time).total_seconds() / 60))
        session.fee_amount = FeeCalculator(db).calculate(duration)
        session.duration_minutes = duration

    session.is_paid = True
    session.paid_at = dt.utcnow()
    session.payment_method = payment_method
    session.processed_by_user_id = user.id
    db.commit()
    return RedirectResponse("/admin/debts", status_code=302)


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


# ──────────────────────────────────────────────────────────────────
# Fiyatlandırma — ücret dilimleri, abonelik fiyatları, borç limiti
# ──────────────────────────────────────────────────────────────────

_DEFAULT_DEBT_THRESHOLD = 500.0


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(
    request: Request,
    saved: int | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Park ücret dilimleri, abonelik fiyatları ve borç limiti düzenleme sayfası."""
    config   = db.query(ParkingConfig).first()
    brackets = (
        db.query(ParkingRateBracket)
        .order_by(ParkingRateBracket.display_order)
        .all()
    )
    plans = (
        db.query(SubscriptionPlan)
        .order_by(SubscriptionPlan.display_order)
        .all()
    )

    flash = None
    if saved:
        flash = {"type": "success", "message": translate("pricing_saved", get_request_lang(request))}
    elif error:
        flash = {"type": "error", "message": translate(error, get_request_lang(request))}

    return templates.TemplateResponse(request, "admin/pricing.html", {
        "user": user,
        "config": config,
        "brackets": brackets,
        "plans": plans,
        "default_debt_threshold": _DEFAULT_DEBT_THRESHOLD,
        "flash": flash,
    })


@router.post("/pricing/debt-limit")
async def update_debt_limit(
    debt_block_threshold: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Maksimum borç limitini (giriş/çıkış engelleme eşiği) günceller."""
    if debt_block_threshold < 0:
        return RedirectResponse("/admin/pricing?error=pricing_err_debt", status_code=302)

    config = db.query(ParkingConfig).first()
    if not config:
        config = ParkingConfig()
        db.add(config)
    config.debt_block_threshold = debt_block_threshold
    db.commit()
    return RedirectResponse("/admin/pricing?saved=1", status_code=302)


# ── Ücret dilimleri ────────────────────────────────────────────────

def _valid_bracket(name: str, min_minutes: int, max_minutes: int, price: float) -> bool:
    return bool(name.strip()) and min_minutes >= 0 and max_minutes > min_minutes and price >= 0


@router.post("/pricing/brackets/new")
async def create_bracket(
    name: str = Form(...),
    min_minutes: int = Form(...),
    max_minutes: int = Form(...),
    price: float = Form(...),
    display_order: int = Form(default=0),
    is_active: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Yeni ücret dilimi ekler."""
    if not _valid_bracket(name, min_minutes, max_minutes, price):
        return RedirectResponse("/admin/pricing?error=pricing_err_bracket", status_code=302)

    db.add(ParkingRateBracket(
        name=name.strip(),
        min_minutes=min_minutes,
        max_minutes=max_minutes,
        price=price,
        display_order=display_order,
        is_active=is_active,
    ))
    db.commit()
    return RedirectResponse("/admin/pricing?saved=1", status_code=302)


@router.post("/pricing/brackets/{bracket_id}")
async def update_bracket(
    bracket_id: int,
    name: str = Form(...),
    min_minutes: int = Form(...),
    max_minutes: int = Form(...),
    price: float = Form(...),
    display_order: int = Form(default=0),
    is_active: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Mevcut ücret dilimini günceller."""
    bracket = db.query(ParkingRateBracket).get(bracket_id)
    if not bracket:
        raise HTTPException(404, "Ucret dilimi bulunamadi.")
    if not _valid_bracket(name, min_minutes, max_minutes, price):
        return RedirectResponse("/admin/pricing?error=pricing_err_bracket", status_code=302)

    bracket.name          = name.strip()
    bracket.min_minutes   = min_minutes
    bracket.max_minutes   = max_minutes
    bracket.price         = price
    bracket.display_order = display_order
    bracket.is_active     = is_active
    db.commit()
    return RedirectResponse("/admin/pricing?saved=1", status_code=302)


@router.post("/pricing/brackets/{bracket_id}/delete")
async def delete_bracket(
    bracket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Ücret dilimini siler."""
    bracket = db.query(ParkingRateBracket).get(bracket_id)
    if bracket:
        db.delete(bracket)
        db.commit()
    return RedirectResponse("/admin/pricing?saved=1", status_code=302)


# ── Abonelik planı fiyatları ───────────────────────────────────────

@router.post("/pricing/plans/{plan_id}")
async def update_plan_price(
    plan_id: int,
    price: float = Form(...),
    is_active: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Abonelik planının fiyatını ve aktiflik durumunu günceller."""
    plan = db.query(SubscriptionPlan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Abonelik plani bulunamadi.")
    if price < 0:
        return RedirectResponse("/admin/pricing?error=pricing_err_price", status_code=302)

    plan.price     = price
    plan.is_active = is_active
    db.commit()
    return RedirectResponse("/admin/pricing?saved=1", status_code=302)
