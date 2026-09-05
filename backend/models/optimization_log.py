from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class OptimizationLog(Base):
    """
    Table to store MILP solver outputs, recommended chartering allocations, and cost savings.
    """
    __tablename__ = "optimization_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )
    route: Mapped[str] = mapped_column(String(100), nullable=False)
    vessel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recommended_charter_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_savings: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)

    def __repr__(self) -> str:
        return (
            f"<OptimizationLog(route={self.route}, vessel={self.vessel_type}, "
            f"date={self.recommended_charter_date}, cost=${self.estimated_total_cost:,.2f})>"
        )
