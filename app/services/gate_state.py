"""
Kapı/ışık durumu — Arduino polling için paylaşımlı bellek içi durum.

camera.py giriş/çıkış kararı verdikten sonra buraya yazar.
Arduino /api/arduino/state endpoint'ini polling yaparak okur.

Durum GATE_OPEN_DURATION saniye sonra otomatik olarak 0'a (kırmızı) döner.
"""

from __future__ import annotations

import time

from app.config import settings

_signal: int = 0          # 1 = yeşil, 0 = kırmızı
_updated_at: float = 0.0  # Son güncelleme zamanı (epoch saniye)


def set_signal(value: int) -> None:
    """Giriş/çıkış kararı sonrası çağrılır. value: 1 (yeşil) veya 0 (kırmızı)."""
    global _signal, _updated_at
    _signal = value
    _updated_at = time.monotonic()


def get_signal() -> int:
    """
    Mevcut ışık sinyalini döner.
    GATE_OPEN_DURATION saniyesi geçmişse otomatik 0'a döner.
    """
    if _signal == 1:
        elapsed = time.monotonic() - _updated_at
        if elapsed >= settings.GATE_OPEN_DURATION:
            return 0
    return _signal
