from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.subscription import Subscription


class SubscriptionPlan(Base):
    """Abonelik planları — saatlik, günlük, aylık vb."""

    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    plan_type: Mapped[str] = mapped_column(
        Enum(
            "hourly", "daily", "weekly", "monthly",
            "quarterly", "biannual", "annual",
            name="plan_type_enum",
        ),
        nullable=False,
    )
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # İlişkiler
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="plan"
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan {self.name} ({self.duration_hours}h) ₺{self.price}>"
