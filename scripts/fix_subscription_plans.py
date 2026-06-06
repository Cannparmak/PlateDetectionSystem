"""
Tek seferlik düzeltme — abonelik planlarını yeni politikaya çeker.

Yapılanlar:
  1. Saatlik / Günlük / Haftalık planları kaldırır (abonelik artık en az aylık).
     - Bu planlara bağlı abonelik varsa silmez, yalnızca pasifleştirir (FK güvenliği).
  2. Kalan planları (aylık, 3 aylık, 6 aylık, yıllık) misafir ücret dilimlerine
     uyumlu fiyatlara ve düzgün sıralamaya günceller.

Kullanım:
    python -m scripts.fix_subscription_plans
"""

from __future__ import annotations

from app.database import SessionLocal
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan

# Kaldırılacak plan tipleri (abonelik en az aylık)
_REMOVE_TYPES = ("hourly", "daily", "weekly")

# plan_type -> (yeni fiyat, yeni display_order)
_UPDATE = {
    "monthly":   (3500.0, 1),
    "quarterly": (9000.0, 2),
    "biannual":  (16500.0, 3),
    "annual":    (30000.0, 4),
}


def main() -> None:
    db = SessionLocal()
    try:
        removed, deactivated, updated = 0, 0, 0

        # 1) Saatlik / Günlük / Haftalık
        for plan in db.query(SubscriptionPlan).filter(
            SubscriptionPlan.plan_type.in_(_REMOVE_TYPES)
        ).all():
            sub_count = db.query(Subscription).filter(
                Subscription.plan_id == plan.id
            ).count()
            if sub_count == 0:
                db.delete(plan)
                removed += 1
                print(f"  [SIL]   {plan.name} ({plan.plan_type}) — abonelik yok")
            else:
                plan.is_active = False
                deactivated += 1
                print(f"  [PASIF] {plan.name} ({plan.plan_type}) — {sub_count} abonelik referansı korunuyor")

        # 2) Kalan planların fiyat + sıralama + aktiflik
        for plan_type, (price, order) in _UPDATE.items():
            plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.plan_type == plan_type
            ).first()
            if plan:
                plan.price = price
                plan.display_order = order
                plan.is_active = True
                updated += 1
                print(f"  [GUNCEL] {plan.name}: TL{price:.0f}, sira={order}")

        db.commit()
        print(f"\nTamam — silinen: {removed}, pasif: {deactivated}, guncellenen: {updated}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
