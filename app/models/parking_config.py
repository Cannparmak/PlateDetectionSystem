from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParkingConfig(Base):
    """Otopark genel ayarları — tek satır olması bekleniyor (id=1)."""

    __tablename__ = "parking_config"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="OtoparkPro", nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_capacity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    open_time: Mapped[str] = mapped_column(String(5), default="00:00", nullable=False)  # "08:00"
    close_time: Mapped[str] = mapped_column(String(5), default="23:59", nullable=False)
    debt_block_threshold: Mapped[float] = mapped_column(Float, default=500.0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ParkingConfig {self.name} capacity={self.total_capacity}>"
