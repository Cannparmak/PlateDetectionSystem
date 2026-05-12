"""
Arduino API router — fiziksel ışık kontrolü için minimal endpoint'ler.

Arduino bu endpoint'leri çağırır, cevap olarak sadece 1 veya 0 alır:
    1 → Yeşil ışık (geçiş izinli)
    0 → Kırmızı ışık (geçiş reddedildi)

Kimlik doğrulama: Cookie değil, X-API-Key header'ı kullanılır.
DB'ye hiçbir şey yazılmaz — salt okunur kontrol.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import verify_arduino_key
from app.models.parking_config import ParkingConfig
from app.services.gate_state import get_signal
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from src.postprocess.text_cleaner import PlateCleaner

router = APIRouter(prefix="/api/arduino", tags=["arduino"])

_cleaner = PlateCleaner()
_DEFAULT_DEBT_THRESHOLD = 500.0


def _find_vehicle(db: Session, plate: str) -> Vehicle | None:
    return (
        db.query(Vehicle)
        .options(joinedload(Vehicle.customer))
        .filter(Vehicle.plate_number == plate, Vehicle.is_active == True)
        .first()
    )


def _has_active_subscription(db: Session, vehicle_id: int) -> bool:
    now = datetime.utcnow()
    return (
        db.query(Subscription)
        .filter(
            Subscription.vehicle_id == vehicle_id,
            Subscription.status == "active",
            Subscription.end_date > now,
        )
        .first()
    ) is not None


def _is_inside(db: Session, vehicle_id: int) -> bool:
    return (
        db.query(ParkingSession)
        .filter(ParkingSession.vehicle_id == vehicle_id, ParkingSession.is_active == True)
        .first()
    ) is not None


def _total_debt(db: Session, vehicle_id: int) -> float:
    rows = (
        db.query(ParkingSession.fee_amount)
        .filter(
            ParkingSession.vehicle_id == vehicle_id,
            ParkingSession.is_guest == True,
            ParkingSession.is_paid == False,
            ParkingSession.fee_amount.isnot(None),
            ParkingSession.is_active == False,
        )
        .all()
    )
    return round(sum(r[0] for r in rows if r[0]), 2)


def _debt_threshold(db: Session) -> float:
    config = db.query(ParkingConfig).first()
    return config.debt_block_threshold if config else _DEFAULT_DEBT_THRESHOLD


# ------------------------------------------------------------------
# Endpoint'ler
# ------------------------------------------------------------------

@router.get("/state", dependencies=[Depends(verify_arduino_key)])
async def gate_state():
    """
    Kamera sisteminin son giriş/çıkış kararını döner.

    Arduino bu endpoint'i ~500ms aralıklarla polling yapar.
    Cevap:
        1  → Yeşil ışık (izin verildi)
        0  → Kırmızı ışık (reddedildi veya henüz karar yok)

    Durum, config'deki GATE_OPEN_DURATION saniyesi sonra otomatik 0'a döner.
    """
    return PlainTextResponse(str(get_signal()))


@router.get("/ping", dependencies=[Depends(verify_arduino_key)])
async def ping():
    """Bağlantı testi — Arduino başlangıçta çağırır, 1 alırsa sunucu hazır."""
    return PlainTextResponse("1")


@router.get("/check", dependencies=[Depends(verify_arduino_key)])
async def check_plate(
    plate: str,
    type: str = "entry",
    db: Session = Depends(get_db),
):
    """
    Plaka durum kontrolü — DB'ye yazmaz, sadece 1 veya 0 döner.

    Query params:
        plate : Plaka numarası (örn. 34ABC123)
        type  : "entry" (giriş) veya "exit" (çıkış) — varsayılan "entry"

    Cevap:
        1  → Yeşil ışık yakılsın
        0  → Kırmızı ışık yakılsın
    """
    clean_plate = _cleaner.clean(plate)
    vehicle = _find_vehicle(db, clean_plate)

    if vehicle is None:
        # Sistemde kayıtsız araç — misafir olarak geçiş izni (giriş), çıkış yok
        signal = 1 if type == "entry" else 0
        return PlainTextResponse(str(signal))

    if type == "exit":
        # Çıkış: araç içeride mi?
        signal = 1 if _is_inside(db, vehicle.id) else 0
        return PlainTextResponse(str(signal))

    # Giriş kontrolü
    if _is_inside(db, vehicle.id):
        return PlainTextResponse("0")  # Zaten içeride

    if _has_active_subscription(db, vehicle.id):
        return PlainTextResponse("1")  # Abone — geç

    debt = _total_debt(db, vehicle.id)
    threshold = _debt_threshold(db)
    signal = 0 if debt >= threshold else 1
    return PlainTextResponse(str(signal))
