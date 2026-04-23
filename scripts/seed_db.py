"""
Veritabanı başlangıç verisi (seed).

Oluşturur:
  - Admin + Kasiyer kullanıcıları
  - 7 abonelik planı (saatlik → yıllık)
  - Otopark konfigürasyonu
  - 3 örnek müşteri + araç + aktif abonelik (demo için)

Kullanım:
  python scripts/seed_db.py           # Veriyi ekle (varsa atla)
  python scripts/seed_db.py --reset   # DB'yi sıfırla ve yeniden oluştur
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.customer import Customer
from app.models.parking_config import ParkingConfig
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.vehicle import Vehicle

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------
# Yardımcı
# ------------------------------------------------------------------

def hash_pw(password: str) -> str:
    return pwd_ctx.hash(password)


# ------------------------------------------------------------------
# Seed fonksiyonları
# ------------------------------------------------------------------

def seed_users(db: Session) -> None:
    if db.query(User).first():
        print("  [ATLA] Kullanıcılar zaten mevcut.")
        return

    users = [
        User(
            email=settings.ADMIN_EMAIL,
            username="admin",
            hashed_password=hash_pw(settings.ADMIN_PASSWORD),
            full_name="Sistem Yöneticisi",
            role="admin",
        ),
        User(
            email=settings.KASIYER_EMAIL,
            username="kasiyer",
            hashed_password=hash_pw(settings.KASIYER_PASSWORD),
            full_name="Ahmet Kasiyer",
            role="kasiyer",
        ),
    ]
    db.add_all(users)
    db.commit()
    print(f"  [OK] {len(users)} kullanıcı oluşturuldu.")
    print(f"       Admin:   {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
    print(f"       Kasiyer: {settings.KASIYER_EMAIL} / {settings.KASIYER_PASSWORD}")


def seed_plans(db: Session) -> None:
    if db.query(SubscriptionPlan).first():
        print("  [ATLA] Abonelik planları zaten mevcut.")
        return

    plans = [
        SubscriptionPlan(name="Saatlik",  plan_type="hourly",    duration_hours=1,    price=10.0,   display_order=1),
        SubscriptionPlan(name="Günlük",   plan_type="daily",     duration_hours=24,   price=50.0,   display_order=2),
        SubscriptionPlan(name="Haftalık", plan_type="weekly",    duration_hours=168,  price=200.0,  display_order=3),
        SubscriptionPlan(name="Aylık",    plan_type="monthly",   duration_hours=720,  price=500.0,  display_order=4),
        SubscriptionPlan(name="3 Aylık",  plan_type="quarterly", duration_hours=2160, price=1300.0, display_order=5),
        SubscriptionPlan(name="6 Aylık",  plan_type="biannual",  duration_hours=4320, price=2400.0, display_order=6),
        SubscriptionPlan(name="Yıllık",   plan_type="annual",    duration_hours=8760, price=4200.0, display_order=7),
    ]
    db.add_all(plans)
    db.commit()
    print(f"  [OK] {len(plans)} abonelik planı oluşturuldu.")


def seed_parking_config(db: Session) -> None:
    if db.query(ParkingConfig).first():
        print("  [ATLA] Otopark konfigürasyonu zaten mevcut.")
        return

    config = ParkingConfig(
        name="OtoparkPro Demo",
        address="Örnek Mah. Test Sk. No:1, İstanbul",
        phone="0212 000 00 00",
        total_capacity=settings.PARKING_CAPACITY,
        open_time="00:00",
        close_time="23:59",
    )
    db.add(config)
    db.commit()
    print(f"  [OK] Otopark konfigürasyonu oluşturuldu (kapasite: {settings.PARKING_CAPACITY}).")


def seed_demo_data(db: Session) -> None:
    if db.query(Customer).first():
        print("  [ATLA] Demo müşteriler zaten mevcut.")
        return

    monthly_plan = db.query(SubscriptionPlan).filter_by(plan_type="monthly").first()
    annual_plan  = db.query(SubscriptionPlan).filter_by(plan_type="annual").first()
    admin_user   = db.query(User).filter_by(role="admin").first()

    now = datetime.utcnow()

    # Müşteri 1 — aktif aylık abonelik
    c1 = Customer(
        first_name="Mehmet", last_name="Yılmaz",
        phone="0532 111 22 33", email="mehmet@demo.com",
        portal_password_hash=hash_pw("demo123"),
    )
    db.add(c1)
    db.flush()

    v1 = Vehicle(
        customer_id=c1.id,
        plate_number="34ABC1234",
        plate_display="34 ABC 1234",
        vehicle_type="otomobil",
        brand="Toyota", model="Corolla", color="Beyaz",
    )
    db.add(v1)
    db.flush()

    if monthly_plan:
        s1 = Subscription(
            vehicle_id=v1.id, plan_id=monthly_plan.id,
            start_date=now - timedelta(days=10),
            end_date=now + timedelta(days=20),
            status="active", total_paid=monthly_plan.price,
            payment_simulated=True, payment_date=now - timedelta(days=10),
            created_by_user_id=admin_user.id if admin_user else None,
        )
        db.add(s1)

    # Müşteri 2 — aktif yıllık abonelik
    c2 = Customer(
        first_name="Ayşe", last_name="Kaya",
        phone="0533 222 33 44", email="ayse@demo.com",
        portal_password_hash=hash_pw("demo123"),
    )
    db.add(c2)
    db.flush()

    v2 = Vehicle(
        customer_id=c2.id,
        plate_number="06XY5678",
        plate_display="06 XY 5678",
        vehicle_type="suv",
        brand="BMW", model="X3", color="Siyah",
    )
    db.add(v2)
    db.flush()

    if annual_plan:
        s2 = Subscription(
            vehicle_id=v2.id, plan_id=annual_plan.id,
            start_date=now - timedelta(days=60),
            end_date=now + timedelta(days=305),
            status="active", total_paid=annual_plan.price,
            payment_simulated=True, payment_date=now - timedelta(days=60),
            created_by_user_id=admin_user.id if admin_user else None,
        )
        db.add(s2)

    # Müşteri 3 — süresi dolmuş abonelik
    c3 = Customer(
        first_name="Can", last_name="Demir",
        phone="0534 333 44 55",
    )
    db.add(c3)
    db.flush()

    v3 = Vehicle(
        customer_id=c3.id,
        plate_number="35DEF9012",
        plate_display="35 DEF 9012",
        vehicle_type="otomobil",
        brand="Renault", model="Clio", color="Kırmızı",
    )
    db.add(v3)
    db.flush()

    if monthly_plan:
        s3 = Subscription(
            vehicle_id=v3.id, plan_id=monthly_plan.id,
            start_date=now - timedelta(days=45),
            end_date=now - timedelta(days=15),   # Süresi dolmuş
            status="expired", total_paid=monthly_plan.price,
            payment_simulated=True,
            created_by_user_id=admin_user.id if admin_user else None,
        )
        db.add(s3)

    db.commit()
    print("  [OK] 3 demo müşteri + araç + abonelik oluşturuldu.")
    print("       34ABC1234 -> Mehmet Yilmaz (aktif aylik)")
    print("       06XY5678  -> Ayse Kaya     (aktif yillik)")
    print("       35DEF9012 -> Can Demir     (suresi dolmus)")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Veritabanı seed scripti")
    parser.add_argument("--reset", action="store_true", help="Tüm tabloları sil ve yeniden oluştur")
    args = parser.parse_args()

    if args.reset:
        print("[RESET] Tüm tablolar siliniyor...")
        Base.metadata.drop_all(bind=engine)
        print("[RESET] Tablolar silindi.")

    print("[INFO] Tablolar oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Tablolar hazır.\n")

    db = SessionLocal()
    try:
        print("[SEED] Kullanıcılar...")
        seed_users(db)

        print("[SEED] Abonelik planları...")
        seed_plans(db)

        print("[SEED] Otopark konfigürasyonu...")
        seed_parking_config(db)

        print("[SEED] Demo müşteriler...")
        seed_demo_data(db)

        print("\n[TAMAMLANDI] Veritabanı hazır.")
        print(f"             Dosya: {Path('otopark.db').resolve()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
