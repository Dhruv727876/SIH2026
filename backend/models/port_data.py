from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class PortData(Base):
    """
    Table for port congestion, draft constraints, and logistics bottlenecks.
    Examples: 'Paradip', 'Vizag', 'Haldia', 'Dhamra', 'Port Hedland'.
    """
    __tablename__ = "port_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    port_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    max_draft_meters: Mapped[float] = mapped_column(Float, nullable=False)
    current_waiting_time_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<PortData(port={self.port_name}, max_draft={self.max_draft_meters}m, waiting={self.current_waiting_time_hours}h)>"
