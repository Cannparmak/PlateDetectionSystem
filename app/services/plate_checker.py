"""
Plaka kontrol servisi — otopark iş mantığının kalbi.

Kameradan gelen plaka metnini DB'de arar, kullanıcı tipine göre
(abone / misafir / anonim misafir) karar verir, kapı sinyali üretir.

Kullanıcı tipleri:
    SUBSCRIBER      — Aktif aboneliği olan araç (ücretsiz giriş/çıkış)
    GUEST           — Sistemde kayıtlı ama aboneliği olmayan araç (ücretli)
    ANONYMOUS_GUEST — Sistemde hiç kaydı olmayan araç (otomatik kaydedilir, ücretli)

Aksiyon kodları:
    ALLOW_ENTRY       — Giriş izni (abone)
    ALLOW_GUEST       — Giriş izni (misafir/anonim)
    ALLOW_EXIT        — Çıkış izni (abone, fee=None)
    ALLOW_EXIT_GUEST  — Çıkış izni (misafir, fee hesaplanmış)
    ALREADY_INSIDE    — Araç zaten içeride
    NOT_INSIDE        — Çıkış isteği ama araç içeride değil
    DENY_DEBT         — Borç eşiği aşıldı, giriş reddedildi
    DENY              — Genel red (beklenmedik durum)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.parking_config import ParkingConfig
from app.models.parking_session import ParkingSession
from app.models.subscription import Subscription
from app.models.vehicle import Vehicle
from app.services.fee_calculator import FeeCalculator
from src.postprocess.text_cleaner import PlateCleaner

logger = logging.getLogger(__name__)

_EXPIRY_WARNING_DAYS = 3
_DEFAULT_DEBT_THRESHOLD = 500.0


@dataclass
class CheckResult:
    """Plaka kontrol sonucu — kapı kararı + UI mesajı."""

    plate_text:         str
    vehicle_found:      bool
    subscription_active: bool
    action:             str        # Aksiyon kodu
    message:            str
    gate_signal:        int        # 1 = aç, 0 = reddet
    user_type:          str = "unknown"   # subscriber / guest / anonymous_guest
    customer_name:      str | None = None
    subscription_info:  dict | None = None
    session_id:         int | None = None
    expiry_warning:     bool = False
    fuzzy_match:        bool = False
    fuzzy_original:     str | None = None
    fee_amount:         float | None = None   # Çıkışta hesaplanan ücret
    total_debt:         float = 0.0           # Mevcut toplam borç
    bracket_name:       str | None = None     # "1-2 Saat" gibi dilim adı


class PlateChecker:
    """
    Giriş/çıkış plaka doğrulama servisi.

    Her istek için yeni bir instance oluşturun:
        checker = PlateChecker(db)
    """

    def __init__(self, db: Session) -> None:
        self._db      = db
        self._cleaner = PlateCleaner()
        self._fee_calc = FeeCalculator(db)

    # ------------------------------------------------------------------
    # Giriş kontrolü
    # ------------------------------------------------------------------

    def check_entry(self, plate_text: str, confidence: float | None = None) -> CheckResult:
        """
        Araç girişi için plaka kontrolü.

        Akış:
        1. Plakayı normalize et
        2. DB'de ara — bulunamazsa anonim araç oluştur
        3. Aktif abonelik var mı?
           → Evet: ALLOW_ENTRY (abone)
           → Hayır: Borç eşiğini kontrol et
             → Borç < eşik: ALLOW_GUEST
             → Borç ≥ eşik: DENY_DEBT
        4. Zaten içeride mi? → ALREADY_INSIDE
        5. Session aç
        """
        plate         = self._normalize(plate_text)
        fuzzy_match   = False
        fuzzy_original: str | None = None

        vehicle, fuzzy_match, fuzzy_original = self._resolve_vehicle(plate)

        if vehicle:
            plate = vehicle.plate_number  # fuzzy ise DB'deki doğru plakayı kullan
        else:
            # Sistemde yok — anonim araç oluştur
            vehicle = self._create_anonymous_vehicle(plate)
            logger.info("Anonim arac olusturuldu: %s", plate)

        customer_name = vehicle.customer.full_name if vehicle.customer else None
        total_debt    = self._get_total_debt(vehicle.id)

        # Zaten içeride mi?
        active_session = self._get_active_session(vehicle.id)
        if active_session:
            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=False,
                action="ALREADY_INSIDE",
                message=f"{plate} — Arac zaten otoparkta. Giris: {active_session.entry_time.strftime('%H:%M')}",
                gate_signal=0,
                user_type="guest" if active_session.is_guest else "subscriber",
                customer_name=customer_name,
                session_id=active_session.id,
                total_debt=total_debt,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # Aktif abonelik kontrolü
        subscription = self._get_active_subscription(vehicle.id)

        if subscription:
            # ── ABONE GİRİŞİ ──────────────────────────────────────────
            session = ParkingSession(
                vehicle_id=vehicle.id,
                subscription_id=subscription.id,
                entry_plate_confidence=confidence,
                is_active=True,
                is_guest=False,
            )
            self._db.add(session)
            self._db.flush()

            expiry_warning = subscription.days_remaining <= _EXPIRY_WARNING_DAYS
            sub_info       = self._subscription_info(subscription)
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
                user_type="subscriber",
                customer_name=customer_name,
                subscription_info=sub_info,
                session_id=session.id,
                expiry_warning=expiry_warning,
                total_debt=total_debt,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # ── MİSAFİR / ANONIM GİRİŞİ ──────────────────────────────────
        threshold = self._get_debt_threshold()
        if total_debt >= threshold:
            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=False,
                action="DENY_DEBT",
                message=(
                    f"{plate} — Odenmemis borcunuz (TL{total_debt:.0f}) esik degeri "
                    f"(TL{threshold:.0f}) asiyor. Lutfen borc odeyiniz."
                ),
                gate_signal=0,
                user_type="guest" if not vehicle.is_anonymous else "anonymous_guest",
                customer_name=customer_name,
                total_debt=total_debt,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        user_type = "anonymous_guest" if vehicle.is_anonymous else "guest"
        session = ParkingSession(
            vehicle_id=vehicle.id,
            subscription_id=None,
            entry_plate_confidence=confidence,
            is_active=True,
            is_guest=True,
        )
        self._db.add(session)
        self._db.flush()

        debt_warning = f" | Mevcut borcunuz: TL{total_debt:.0f}" if total_debt > 0 else ""
        msg = f"Misafir girisi — {plate}{debt_warning}"

        return CheckResult(
            plate_text=plate,
            vehicle_found=True,
            subscription_active=False,
            action="ALLOW_GUEST",
            message=msg,
            gate_signal=1,
            user_type=user_type,
            customer_name=customer_name,
            session_id=session.id,
            total_debt=total_debt,
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
        1. Plakayı normalize et — DB'de ara
        2. Aktif session var mı? → yoksa NOT_INSIDE
        3. Session kapat:
           - Abone: fee_amount = None (ücretsiz)
           - Misafir: FeeCalculator ile ücret hesapla, session'a kaydet
        """
        plate         = self._normalize(plate_text)
        fuzzy_match   = False
        fuzzy_original: str | None = None

        vehicle, fuzzy_match, fuzzy_original = self._resolve_vehicle(plate)

        if vehicle is None:
            return CheckResult(
                plate_text=plate,
                vehicle_found=False,
                subscription_active=False,
                action="DENY",
                message=f"Plaka bulunamadi: {plate}",
                gate_signal=0,
            )

        plate         = vehicle.plate_number
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

        # Session kapat — önce süreyi hesapla
        active_session.close(confidence=confidence)
        duration = active_session.duration_minutes or 0

        is_subscriber = active_session.subscription_id is not None

        if is_subscriber:
            # ── ABONE ÇIKIŞI — ücretsiz ──────────────────────────────
            active_session.fee_amount = None
            active_session.is_paid    = True   # Abonelik kapsar, "ödendi" say
            self._db.flush()

            subscription = self._get_subscription_by_id(active_session.subscription_id)
            sub_info     = self._subscription_info(subscription) if subscription else None
            duration_str = f"{duration} dakika"

            return CheckResult(
                plate_text=plate,
                vehicle_found=True,
                subscription_active=True,
                action="ALLOW_EXIT",
                message=f"Cikis izni — {customer_name or plate} ({duration_str})",
                gate_signal=1,
                user_type="subscriber",
                customer_name=customer_name,
                subscription_info=sub_info,
                session_id=active_session.id,
                fee_amount=None,
                fuzzy_match=fuzzy_match,
                fuzzy_original=fuzzy_original,
            )

        # ── MİSAFİR ÇIKIŞI — ücret hesapla ──────────────────────────
        fee          = self._fee_calc.calculate(duration)
        bracket_name = self._fee_calc.get_bracket_name(duration)

        active_session.fee_amount = fee
        active_session.is_paid    = False
        self._db.flush()

        total_debt = self._get_total_debt(vehicle.id)
        user_type  = "anonymous_guest" if vehicle.is_anonymous else "guest"

        h, m = divmod(duration, 60)
        duration_str = f"{h} saat {m} dk" if h else f"{m} dk"
        msg = f"Misafir cikis — {plate} | {duration_str} | Ucret: TL{fee:.0f} ({bracket_name})"

        return CheckResult(
            plate_text=plate,
            vehicle_found=True,
            subscription_active=False,
            action="ALLOW_EXIT_GUEST",
            message=msg,
            gate_signal=1,
            user_type=user_type,
            customer_name=customer_name,
            session_id=active_session.id,
            fee_amount=fee,
            total_debt=total_debt,
            bracket_name=bracket_name,
            fuzzy_match=fuzzy_match,
            fuzzy_original=fuzzy_original,
        )

    # ------------------------------------------------------------------
    # Yardımcı: araç çözümleme
    # ------------------------------------------------------------------

    def _resolve_vehicle(
        self, plate: str
    ) -> tuple[Vehicle | None, bool, str | None]:
        """
        Plakayı önce exact, sonra fuzzy arar.
        Returns: (vehicle, fuzzy_match, fuzzy_original)
        """
        vehicle = self._find_vehicle(plate)
        if vehicle:
            return vehicle, False, None

        fuzzy = self._find_vehicle_fuzzy(plate)
        if fuzzy:
            v, _ = fuzzy
            return v, True, plate

        return None, False, None

    def _create_anonymous_vehicle(self, plate: str) -> Vehicle:
        """Sistemde kayıtsız plaka için anonim araç kaydı oluşturur."""
        from src.postprocess.text_cleaner import PlateCleaner
        cleaner = PlateCleaner()
        vehicle = Vehicle(
            customer_id=None,
            is_anonymous=True,
            plate_number=plate,
            plate_display=cleaner.to_display(plate),
            vehicle_type="otomobil",
            is_active=True,
        )
        self._db.add(vehicle)
        self._db.flush()
        return vehicle

    # ------------------------------------------------------------------
    # Yardımcı: borç sorgulama
    # ------------------------------------------------------------------

    def _get_total_debt(self, vehicle_id: int) -> float:
        """Araca ait ödenmemiş toplam borç."""
        rows = (
            self._db.query(ParkingSession.fee_amount)
            .filter(
                ParkingSession.vehicle_id == vehicle_id,
                ParkingSession.is_guest == True,
                ParkingSession.is_paid == False,
                ParkingSession.fee_amount.isnot(None),
                ParkingSession.is_active == False,  # Tamamlanmış oturumlar
            )
            .all()
        )
        return round(sum(r[0] for r in rows if r[0]), 2)

    def _get_debt_threshold(self) -> float:
        """parking_config'den borç eşiğini okur."""
        config = self._db.query(ParkingConfig).first()
        return config.debt_block_threshold if config else _DEFAULT_DEBT_THRESHOLD

    # ------------------------------------------------------------------
    # Yardımcı: DB sorguları
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

    def _find_vehicle_fuzzy(
        self, plate: str, max_distance: int = 2
    ) -> tuple[Vehicle, int] | None:
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
                best_dist    = dist
                best_vehicle = v
        return (best_vehicle, best_dist) if best_vehicle else None

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
            "plan_name":      sub.plan.name if sub.plan else "?",
            "end_date":       sub.end_date.strftime("%d.%m.%Y"),
            "days_remaining": sub.days_remaining,
        }
