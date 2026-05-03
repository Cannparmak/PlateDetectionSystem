"""
Misafir otopark ücreti hesaplama servisi.

Türkiye standardı dilim bazlı ücretlendirme:
    Araç hangi zaman dilimine giriyorsa o dilimiın sabit ücretini öder.
    1 saat 1 dakika → "1-2 Saat" dilimine girer → o dilimiın tam fiyatı.

Kullanım:
    calc = FeeCalculator(db)
    fee = calc.calculate(duration_minutes=75)   # → 80.0
    fee = calc.calculate(duration_minutes=20)   # → 0.0 (tolerans)
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.parking_rate_bracket import ParkingRateBracket

logger = logging.getLogger(__name__)


class FeeCalculator:
    """
    DB'deki parking_rate_brackets tablosunu kullanarak
    kalış süresi bazlı ücret hesaplar.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def calculate(self, duration_minutes: int) -> float:
        """
        Kalış süresine göre ücret hesaplar.

        Args:
            duration_minutes: Giriş-çıkış arası dakika farkı

        Returns:
            TL cinsinden ücret (float). Tolerans süresi içindeyse 0.0.
        """
        if duration_minutes <= 0:
            return 0.0

        brackets = (
            self._db.query(ParkingRateBracket)
            .filter(ParkingRateBracket.is_active == True)
            .order_by(ParkingRateBracket.display_order)
            .all()
        )

        if not brackets:
            logger.warning("Ücret dilimi tablosu boş — varsayılan saatlik ücret uygulanıyor.")
            return self._fallback_rate(duration_minutes)

        daily_cap_minutes = 24 * 60   # 1440 dakika

        # 24 saatten uzun kalışlar: tam günler + kalan dakika
        full_days    = duration_minutes // daily_cap_minutes
        remaining    = duration_minutes % daily_cap_minutes

        daily_max_price = brackets[-1].price  # Son dilim = günlük tavan

        day_fee = self._bracket_fee(remaining, brackets)
        total   = (full_days * daily_max_price) + day_fee

        logger.debug(
            "Ücret: %d dk → %d tam gün (₺%.0f) + %d dk kalan (₺%.0f) = ₺%.0f",
            duration_minutes, full_days, full_days * daily_max_price,
            remaining, day_fee, total,
        )
        return round(total, 2)

    @staticmethod
    def _bracket_fee(minutes: int, brackets: list[ParkingRateBracket]) -> float:
        """Dakikayı ilgili dilime eşleştirir ve o dilimiın fiyatını döndürür."""
        for bracket in brackets:
            if bracket.min_minutes < minutes <= bracket.max_minutes:
                return bracket.price
        # minutes == 0 veya hiçbir dilimle eşleşmiyorsa (normalde olmamalı)
        return 0.0

    @staticmethod
    def _fallback_rate(duration_minutes: int) -> float:
        """Dilim tablosu boşsa saat başı ₺50 varsayılan."""
        hours = (duration_minutes + 59) // 60
        return float(hours * 50)

    def get_bracket_name(self, duration_minutes: int) -> str:
        """Kullanıcıya gösterilecek dilim adını döndürür."""
        if duration_minutes <= 0:
            return "—"

        remaining = duration_minutes % (24 * 60)
        brackets  = (
            self._db.query(ParkingRateBracket)
            .filter(ParkingRateBracket.is_active == True)
            .order_by(ParkingRateBracket.display_order)
            .all()
        )

        for bracket in brackets:
            if bracket.min_minutes < remaining <= bracket.max_minutes:
                return bracket.name

        return "Günlük Tavan"
