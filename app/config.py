"""
Uygulama ayarları — .env dosyasından okunur.

Kullanım:
    from app.config import settings
    print(settings.MODEL_PATH)
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Genel
    APP_NAME: str = "CanPark"
    SECRET_KEY: str = "change-this-in-production-super-secret"

    # Veritabanı
    DATABASE_URL: str = "sqlite:///./otopark.db"

    # ML Model
    MODEL_PATH: str = "models/plate_det_global_v1_best.pt"
    OCR_LANGUAGES: str = "tr,en"
    YOLO_CONF: float = 0.25

    # Dosya yükleme
    UPLOAD_DIR: str = "outputs/uploads"
    RESULTS_DIR: str = "outputs/results"
    MAX_UPLOAD_MB: int = 20

    # Varsayılan kullanıcılar (seed)
    ADMIN_EMAIL: str = "admin@otopark.local"
    ADMIN_PASSWORD: str = "admin123"
    KASIYER_EMAIL: str = "kasiyer@otopark.local"
    KASIYER_PASSWORD: str = "kasiyer123"

    # Otopark
    PARKING_CAPACITY: int = 100

    # Telefon ülke kodu (+90 Türkiye, +1 ABD, vb.)
    PHONE_COUNTRY_CODE: str = "+90"

    # Gate controller (seri port)
    GATE_ENABLED: bool = False
    GATE_PORT: str = "COM3"        # Windows: COM3, Linux: /dev/ttyUSB0
    GATE_BAUDRATE: int = 9600
    GATE_OPEN_CMD: str = "1"       # Porta gönderilecek açma komutu
    GATE_CLOSE_CMD: str = "0"      # Porta gönderilecek kapama komutu
    GATE_OPEN_DURATION: int = 5    # Kaç saniye açık kalacak (0 = manuel kapat)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def ocr_language_list(self) -> list[str]:
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",")]

    @property
    def model_path_abs(self) -> str:
        return str(Path(self.MODEL_PATH).resolve())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
