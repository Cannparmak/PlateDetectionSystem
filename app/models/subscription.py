from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.subscription_plan import SubscriptionPlan
    from app.models.user import User


class Subscription(Base):
    """Araç abonelikleri — hangi araç hangi planla ne zaman kadar geçerli."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_plans.id"), nullable=False
    )
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "expired", "cancelled", "pending", name="subscription_status"),
        nullable=False,
        default="active",
        index=True,
    )
    total_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payment_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # İlişkiler
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="subscriptions")
    created_by: Mapped["User | None"] = relationship("User")

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.end_date > datetime.utcnow()

    @property
    def days_remaining(self) -> int:
        if not self.is_active:
            return 0
        return max(0, (self.end_date - datetime.utcnow()).days)

    def __repr__(self) -> str:
        return f"<Subscription vehicle={self.vehicle_id} status={self.status} ends={self.end_date.date()}>"
