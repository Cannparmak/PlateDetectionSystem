"""
Test amaçlı borç kaydı ekler.
66 AR 428 plakalı araç için 600 TL ödenmemiş borç oluşturur.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.parking_session import ParkingSession
from src.postprocess.text_cleaner import PlateCleaner

PLATE_RAW = "66 AR 428"
DEBT_AMOUNT = 600.0

cleaner = PlateCleaner()
plate_number = cleaner.clean(PLATE_RAW)
plate_display = cleaner.to_display(plate_number) if hasattr(cleaner, "to_display") else PLATE_RAW

db = SessionLocal()
try:
    vehicle = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
    if not vehicle:
        vehicle = Vehicle(
            customer_id=None,
            is_anonymous=True,
            plate_number=plate_number,
            plate_display=plate_display,
            vehicle_type="otomobil",
            is_active=True,
        )
        db.add(vehicle)
        db.flush()
        print(f"Yeni araç oluşturuldu: {plate_number}")
    else:
        print(f"Mevcut araç bulundu: {plate_number} (id={vehicle.id})")

    entry = datetime.utcnow() - timedelta(hours=3)
    exit_ = datetime.utcnow() - timedelta(hours=1)
    session = ParkingSession(
        vehicle_id=vehicle.id,
        subscription_id=None,
        entry_time=entry,
        exit_time=exit_,
        duration_minutes=120,
        is_active=False,
        is_guest=True,
        fee_amount=DEBT_AMOUNT,
        is_paid=False,
    )
    db.add(session)
    db.commit()
    print(f"Borç kaydı eklendi: {DEBT_AMOUNT} TL — araç id={vehicle.id}")
    print(f"Artık '{plate_number}' plakasına giriş talebi gelince DENY_DEBT döner.")
finally:
    db.close()
