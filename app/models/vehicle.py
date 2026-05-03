from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.subscription import Subscription
    from app.models.parking_session import ParkingSession


class Vehicle(Base):
    """Müşteriye ait araçlar ve plakalar."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Normalize edilmiş plaka — boşluksuz büyük harf (DB araması için)
    plate_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    # Orijinal gösterim formatı "34 ABC 1234" (UI için)
    plate_display: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="otomobil"
    )  # otomobil / suv / minibüs / kamyonet
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # İlişkiler
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="vehicles")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="vehicle", cascade="all, delete-orphan"
    )
    parking_sessions: Mapped[list["ParkingSession"]] = relationship(
        "ParkingSession", back_populates="vehicle"
    )

    def __repr__(self) -> str:
        return f"<Vehicle {self.plate_number}>"
