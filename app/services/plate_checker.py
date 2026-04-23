"""
Plaka kontrol servisi — otopark iş mantığının kalbi.

Kameradan gelen plaka metnini DB'de arar, abonelik durumunu kontrol eder
ve kapıya gönderilecek kararı (ALLOW / DENY) üretir.

Kullanım:
    checker = PlateChecker(db)
    result = checker.check_entry("34ABC1234")
    if result.action == "ALLOW_ENTRY":
        gate_controller.open()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session, joinedload

from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from src.postprocess.text_cleaner import PlateCleaner

# Abonelik bitmesine kaç gün kaldıysa uyarı ver
_EXPIRY_WARNING_DAYS = 3


@dataclass
class CheckResult:
    """Plaka kontrol sonucu — kapı kararı + kullanıcıya mesaj."""
    plate_text: str
    vehicle_found: bool
    subscription_active: bool
    action: str                        # "ALLOW_ENTRY" | "ALLOW_EXIT" | "DENY" | "EXPIRED" | "ALREADY_INSIDE" | "NOT_INSIDE"
    message: str                       # Ekranda gösterilecek mesaj
    gate_signal: int                   # 1 = aç, 0 = kapat/reddet
    customer_name: str | None = None
    subscription_info: dict | None = None   # plan adı, bitiş tarihi, kalan gün
    session_id: int | None = None           # Açılan/kapatılan session ID
    expiry_warning: bool = False            # Abonelik bitmek üzere mi?
    fuzzy_match: bool = False               # Plaka yakın eşleşme ile mi bulundu?
    fuzzy_original: str | None = None      # Kameradan okunan orijinal plaka (fuzzy ise)


class PlateChecker:
    """
    Giriş/çıkış plaka doğrulama servisi.

    Her istek için yeni bir instance oluşturun (DB session inject edilir):
        checker = PlateChecker(db)
    """

    def __init__(self, db: Session):
        self._db = db
        self._cleaner = PlateCleaner()

    # ------------------------------------------------------------------
    # Giriş kontrolü
    # ------------------------------------------------------------------

    def check_entry(self, plate_text: str, confidence: float | None = None) -> CheckResult:
        """
        Araç girişi için plaka kontrolü.

        Akış:
        1. Plakayı normalize et
        2. DB'de ara → bulunamazsa DENY
        3. Aktif abonelik var mı? → yoksa DENY/EXPIRED
        4. Zaten içeride mi? → ALREADY_INSIDE
        5. Her şey tamam → ALLOW_ENTRY + session aç
        """
        plate = self._normalize(plate_text)
        fuzzy_match = False
        fuzzy_original: str | None = None

        vehicle = self._find_vehicle(plate)
        if vehicle is None:
            # Exact eşleşme yok — yakın plaka ara
            fuzzy_result = self._find_vehicle_fuzzy(plate)
            if fuzzy_result:
                vehicle, dist = fuzzy_result
                fuzzy_match = True
                fuzzy_original = plate
                plate = vehicle.plate_number  # DB'deki doğru plaka ile devam et
            else:
                return CheckResult(
                    plate_text=plate,
                    vehicle_found=False,
                    subscription_active=False,
                    action="DENY",
                    message=f"Plaka bulunamadi: {plate} — Abonelik yok veya kayitsiz arac.",
                    gate_signal=0,
                )

        customer_name = vehicle.customer.full_name if vehicle.customer else None

        # Aktif abonelik kontrolü
        subscription = self._get_active_subscription(vehicle.id)
        if subscription is None:
            # Son abonelik süresi dolmuş mu?
            expired = self._get_last_subscription(vehicle.id)
            if expired:
                return CheckResult(
                    plate_text=plate,
                    vehicle_found=True,
                    subscription_active=False,
                    action="EXPIRED",
                    message=f"{plate} — Abonelik suresi dolmus. Yenileme gerekiyor.",
                    gate_signal=0,
                    customer_name=customer_name,
                    fuzzy_match=fuzzy_match,
                    fuzzy_original=fuzzy_original,
                )
            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=False,
                action="DENY",
                message=f"{plate} — Aktif abonelik yok.",
                gate_signal=0,
                customer_name=customer_name,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # Zaten içeride mi?
        active_session = self._get_active_session(vehicle.id)
        if active_session:
            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=True,
                action="ALREADY_INSIDE",
                message=f"{plate} — Arac zaten otoparkta. Giris: {active_session.entry_time.strftime('%H:%M')}",
                gate_signal=0,
                customer_name=customer_name,
                session_id=active_session.id,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # Her şey tamam — session aç
        session = ParkingSession(
            vehicle_id=vehicle.id,
            subscription_id=subscription.id,
            entry_plate_confidence=confidence,
            is_active=True,
        )
        self._db.add(session)
        self._db.flush()  # ID alabilmek için

        # Abonelik bitiş uyarısı
        expiry_warning = subscription.days_remaining <= _EXPIRY_WARNING_DAYS
        sub_info = self._subscription_info(subscription)

        if fuzzy_match:
            logger.info("Fuzzy esleme: kamera=%s, DB=%s", fuzzy_original, plate)
        msg = f"Giris izni verildi — {customer_name or plate}"
        if expiry_warning:
            msg += f" (UYARI: Abonelik {subscription.days_remaining} gun icinde bitiyor!)"

        return CheckResult(
            plate_text=plate,
            vehicle_found=True,
            subscription_active=True,
            action="ALLOW_ENTRY",
            message=msg,
            gate_signal=1,
            customer_name=customer_name,
            subscription_info=sub_info,
            session_id=session.id,
            expiry_warning=expiry_warning,
            fuzzy_match=fuzzy_match,
            fuzzy_original=fuzzy_original,
        )

    # ------------------------------------------------------------------
    # Çıkış kontrolü
    # ------------------------------------------------------------------

    def check_exit(self, plate_text: str, confidence: float | None = None) -> CheckResult:
        """
        Araç çıkışı için plaka kontrolü.

        Akış:
        1. Plakayı normalize et
        2. DB'de ara → bulunamazsa DENY
        3. Aktif session var mı? → yoksa NOT_INSIDE
        4. Session kapat → ALLOW_EXIT
        """
        plate = self._normalize(plate_text)
        fuzzy_match = False
        fuzzy_original: str | None = None

        vehicle = self._find_vehicle(plate)
        if vehicle is None:
            fuzzy_result = self._find_vehicle_fuzzy(plate)
            if fuzzy_result:
                vehicle, dist = fuzzy_result
                fuzzy_match = True
                fuzzy_original = plate
                plate = vehicle.plate_number
            else:
                return CheckResult(
                    plate_text=plate,
                    vehicle_found=False,
                    subscription_active=False,
                    action="DENY",
                    message=f"Plaka bulunamadi: {plate}",
                    gate_signal=0,
                )

        customer_name = vehicle.customer.full_name if vehicle.customer else None

        active_session = self._get_active_session(vehicle.id)
        if active_session is None:
            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=False,
                action="NOT_INSIDE",
                message=f"{plate} — Arac otoparkta bulunmuyor.",
                gate_signal=0,
                customer_name=customer_name,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # Session kapat
        active_session.close(confidence=confidence)
        self._db.flush()

        subscription = self._get_subscription_by_id(active_session.subscription_id)
        sub_info = self._subscription_info(subscription) if subscription else None

        if fuzzy_match:
            logger.info("Fuzzy esleme: kamera=%s, DB=%s", fuzzy_original, plate)
        duration_str = f"{active_session.duration_minutes} dakika" if active_session.duration_minutes else "?"
        msg = f"Cikis izni verildi — {customer_name or plate} ({duration_str})"

        return CheckResult(
            plate_text=plate,
            vehicle_found=True,
            subscription_active=True,
            action="ALLOW_EXIT",
            message=msg,
            gate_signal=1,
            customer_name=customer_name,
            subscription_info=sub_info,
            session_id=active_session.id,
            fuzzy_match=fuzzy_match,
            fuzzy_original=fuzzy_original,
        )

    # ------------------------------------------------------------------
    # Yardımcı metodlar
    # ------------------------------------------------------------------

    def _normalize(self, plate_text: str) -> str:
        return self._cleaner.clean(plate_text)

    def _find_vehicle(self, plate: str) -> Vehicle | None:
        return (
            self._db.query(Vehicle)
            .options(joinedload(Vehicle.customer))
            .filter(Vehicle.plate_number == plate, Vehicle.is_active == True)
            .first()
        )

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        """İki string arası minimum düzenleme mesafesi (Levenshtein)."""
        if len(a) < len(b):
            a, b = b, a
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for ca in a:
            curr = [prev[0] + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
            prev = curr
        return prev[-1]

    def _find_vehicle_fuzzy(self, plate: str, max_distance: int = 2) -> tuple[Vehicle, int] | None:
        """
        Exact eşleşme yoksa yakın plakalarda arar.

        Returns:
            (vehicle, distance) veya None
        """
        # Sadece aktif araçları çek, tüm plakalarla karşılaştır
        vehicles = (
            self._db.query(Vehicle)
            .options(joinedload(Vehicle.customer))
            .filter(Vehicle.is_active == True)
            .all()
        )
        best_vehicle: Vehicle | None = None
        best_dist = max_distance + 1
        for v in vehicles:
            dist = self._levenshtein(plate, v.plate_number)
            if dist <= max_distance and dist < best_dist:
                best_dist = dist
                best_vehicle = v
        if best_vehicle is None:
            return None
        return best_vehicle, best_dist

    def _get_active_subscription(self, vehicle_id: int) -> Subscription | None:
        now = datetime.utcnow()
        return (
            self._db.query(Subscription)
            .options(joinedload(Subscription.plan))
            .filter(
                Subscription.vehicle_id == vehicle_id,
                Subscription.status == "active",
                Subscription.end_date > now,
            )
            .order_by(Subscription.end_date.desc())
            .first()
        )

    def _get_last_subscription(self, vehicle_id: int) -> Subscription | None:
        return (
            self._db.query(Subscription)
            .filter(Subscription.vehicle_id == vehicle_id)
            .order_by(Subscription.end_date.desc())
            .first()
        )

    def _get_active_session(self, vehicle_id: int) -> ParkingSession | None:
        return (
            self._db.query(ParkingSession)
            .filter(
                ParkingSession.vehicle_id == vehicle_id,
                ParkingSession.is_active == True,
            )
            .first()
        )

    def _get_subscription_by_id(self, sub_id: int | None) -> Subscription | None:
        if sub_id is None:
            return None
        return self._db.query(Subscription).get(sub_id)

    @staticmethod
    def _subscription_info(sub: Subscription) -> dict:
        return {
            "plan_name": sub.plan.name if sub.plan else "?",
            "end_date": sub.end_date.strftime("%d.%m.%Y"),
            "days_remaining": sub.days_remaining,
        }
