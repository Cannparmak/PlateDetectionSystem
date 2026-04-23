"""
Kapı/bariyer kontrolcüsü — seri port üzerinden röle/Arduino'ya sinyal gönderir.

Konfigurasyon (.env):
    GATE_ENABLED=true
    GATE_PORT=COM3          # Windows; Linux: /dev/ttyUSB0
    GATE_BAUDRATE=9600
    GATE_OPEN_CMD=1
    GATE_CLOSE_CMD=0
    GATE_OPEN_DURATION=5    # saniye, 0 = manuel kapat

GATE_ENABLED=false iken tüm metodlar sessizce çalışır — donanım olmadan
uygulama sorunsuz çalışır, sadece log mesajı yazar.

Kullanım:
    gate = GateController.get_instance()
    gate.open()    # "1\\n" gönderir → kapı açılır
    gate.close()   # "0\\n" gönderir → kapı kapanır
"""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)


class GateController:
    """
    Bariyer/kapı kontrolcüsü — singleton.
    GATE_ENABLED=false iken stub modda çalışır (donanım gerekmez).
    """

    _instance: GateController | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        from app.config import settings
        self._enabled = settings.GATE_ENABLED
        self._port = settings.GATE_PORT
        self._baudrate = settings.GATE_BAUDRATE
        self._open_cmd = settings.GATE_OPEN_CMD
        self._close_cmd = settings.GATE_CLOSE_CMD
        self._open_duration = settings.GATE_OPEN_DURATION
        self._serial = None
        self._auto_close_task: asyncio.Task | None = None

        if self._enabled:
            self._connect()

    @classmethod
    def get_instance(cls) -> "GateController":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Bağlantı
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        try:
            import serial
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=1,
            )
            logger.info("Gate controller baglandi: %s @ %d baud", self._port, self._baudrate)
        except Exception as e:
            logger.error("Gate controller baglanamadi: %s — %s", self._port, e)
            logger.warning("Kapi kontrol devre disi (donanim yok veya port hatasi).")
            self._serial = None

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Temel komutlar
    # ------------------------------------------------------------------

    def _send(self, cmd: str) -> bool:
        """Porta komut gönderir. Başarılıysa True döner."""
        if not self._enabled:
            logger.debug("Gate [STUB] komut: %s", cmd)
            return True

        if not self.is_connected():
            logger.warning("Gate controller bagli degil, yeniden baglaniliyor...")
            self._connect()

        if not self.is_connected():
            logger.error("Gate komutu gonderilemedi: baglanti yok.")
            return False

        try:
            self._serial.write(f"{cmd}\n".encode("ascii"))
            self._serial.flush()
            logger.info("Gate komutu gonderildi: %s", cmd)
            return True
        except Exception as e:
            logger.error("Gate yazma hatasi: %s", e)
            return False

    def open(self) -> bool:
        """Kapıyı aç — '1\\n' gönderir."""
        success = self._send(self._open_cmd)
        if success and self._open_duration > 0:
            # Auto-close zamanlayıcısını başlat (sync)
            t = threading.Timer(self._open_duration, self.close)
            t.daemon = True
            t.start()
        return success

    def close(self) -> bool:
        """Kapıyı kapat — '0\\n' gönderir."""
        return self._send(self._close_cmd)

    def send_signal(self, signal: int) -> bool:
        """gate_signal değerine göre aç (1) veya kapat (0)."""
        if signal == 1:
            return self.open()
        return self.close()

    # ------------------------------------------------------------------
    # Async wrapper (FastAPI route'larında await ile kullan)
    # ------------------------------------------------------------------

    async def async_open(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.open)

    async def async_close(self) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.close)

    async def async_send_signal(self, signal: int) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send_signal, signal)

    # ------------------------------------------------------------------
    # Temizlik
    # ------------------------------------------------------------------

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self.close()
            self._serial.close()
            logger.info("Gate controller baglantisi kapatildi.")
