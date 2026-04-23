from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.subscription import Subscription


class ParkingSession(Base):
    """Araç giriş/çıkış kayıtları."""

    __tablename__ = "parking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    entry_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )  # True = araç içeride
    entry_plate_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_plate_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exit_snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gate_result: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "OPENED" | "DENIED" | "ERROR"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # İlişkiler
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="parking_sessions")
    subscription: Mapped["Subscription | None"] = relationship("Subscription")

    def close(
        self,
        exit_time: datetime | None = None,
        confidence: float | None = None,
        snapshot_path: str | None = None,
    ) -> None:
        """Çıkış kaydı oluştur — duration_minutes hesapla."""
        self.exit_time = exit_time or datetime.utcnow()
        self.exit_plate_confidence = confidence
        self.exit_snapshot_path = snapshot_path
        self.is_active = False
        delta = self.exit_time - self.entry_time
        self.duration_minutes = max(1, int(delta.total_seconds() / 60))

    def __repr__(self) -> str:
        return f"<ParkingSession vehicle={self.vehicle_id} active={self.is_active}>"
