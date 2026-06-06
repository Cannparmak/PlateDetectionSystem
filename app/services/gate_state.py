"""
Kapı/ışık durumu — Arduino polling için paylaşımlı bellek içi durum.

camera.py giriş/çıkış kararı verdikten sonra buraya yazar:
    - signal     : 1 (yeşil) / 0 (kırmızı)
    - info_line  : LCD 2. satırında gösterilecek borç/abonelik bilgisi (ASCII)

Arduino /api/arduino/state endpoint'ini polling yaparak ikisini de okur.

Sinyal GATE_OPEN_DURATION saniye sonra otomatik olarak 0'a (kırmızı) döner.
Bilgi metni ise sürücünün okuyabilmesi için bir süre daha ekranda kalır.
"""

from __future__ import annotations

import time

from app.config import settings

_signal: int = 0          # 1 = yeşil, 0 = kırmızı
_updated_at: float = 0.0  # Son güncelleme zamanı (epoch saniye)
_info_line: str = ""      # LCD 2. satır metni (borç / abonelik / limit bilgisi)

# Bilgi metninin ekranda kalma süresi (saniye). Reddedilen (kırmızı) araçlarda
# kapı hiç açılmaz ama sürücünün borç/limit yazısını okuyabilmesi için
# en az bu kadar saniye ekranda tutulur.
_INFO_DISPLAY_SECONDS = 8


def set_signal(value: int, info_line: str = "") -> None:
    """
    Giriş/çıkış kararı sonrası çağrılır.

    value     : 1 (yeşil) veya 0 (kırmızı)
    info_line : LCD 2. satırında gösterilecek bilgi (örn. "Borc: 480TL")
    """
    global _signal, _updated_at, _info_line
    _signal = value
    _updated_at = time.monotonic()
    _info_line = info_line or ""


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


def get_info_line() -> str:
    """
    LCD 2. satır bilgisini döner.

    Karar verildikten en fazla _INFO_DISPLAY_SECONDS saniye (veya kapı açık
    kalma süresi, hangisi büyükse) boyunca gösterilir; sonra boş döner.
    """
    if not _info_line:
        return ""
    window = max(settings.GATE_OPEN_DURATION, _INFO_DISPLAY_SECONDS)
    if time.monotonic() - _updated_at >= window:
        return ""
    return _info_line
