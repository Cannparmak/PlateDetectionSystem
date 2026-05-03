from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParkingRateBracket(Base):
    """
    Otopark ücret dilimleri — misafir araçlar için sabit fiyat tarifesi.

    Araç hangi zaman dilimine giriyorsa o dilimiın sabit ücretini öder.
    Örnek: 1 saat 1 dakika kalan araç "1-2 Saat" dilimine girer → ₺80.

    Admin panelinden düzenlenebilir.
    """

    __tablename__ = "parking_rate_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)       # "İlk 1 Saat"
    min_minutes: Mapped[int] = mapped_column(Integer, nullable=False)    # Başlangıç (dahil değil)
    max_minutes: Mapped[int] = mapped_column(Integer, nullable=False)    # Bitiş (dahil)
    price: Mapped[float] = mapped_column(Float, nullable=False)          # ₺ cinsinden sabit ücret
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ParkingRateBracket {self.name} {self.min_minutes}-{self.max_minutes}dk ₺{self.price}>"
