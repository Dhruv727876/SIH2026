from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class MarketData(Base):
    """
    Time-series table for ocean freight rates, bunker fuel, and macro indices.
    Examples for index_name: 'BCI', 'BPI', 'BUNKER_SIN', 'USD_INR', 'C5_FREIGHT'.
    """
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    index_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    def __repr__(self) -> str:
        return f"<MarketData(index={self.index_name}, value={self.value}, time={self.timestamp})>"
