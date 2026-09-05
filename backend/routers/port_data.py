from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models.port_data import PortData
from schemas.port_data import PortDataCreate, PortDataResponse

router = APIRouter(prefix="/api/v1/port-data", tags=["Port Telemetry"])


@router.post(
    "",
    response_model=PortDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest or update port constraint and waiting time data",
)
def create_or_update_port_data(
    payload: PortDataCreate,
    db: Session = Depends(get_db),
):
    """
    Ingests or updates port metrics (draft constraints and congestion waiting times).
    """
    stmt = select(PortData).where(PortData.port_name == payload.port_name)
    existing_port = db.scalars(stmt).first()

    if existing_port:
        existing_port.max_draft_meters = payload.max_draft_meters
        existing_port.current_waiting_time_hours = payload.current_waiting_time_hours
        existing_port.updated_at = datetime.utcnow()
        db_item = existing_port
    else:
        db_item = PortData(
            port_name=payload.port_name,
            max_draft_meters=payload.max_draft_meters,
            current_waiting_time_hours=payload.current_waiting_time_hours,
            updated_at=datetime.utcnow(),
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.get(
    "",
    response_model=List[PortDataResponse],
    summary="Retrieve current port telemetry and constraints",
)
def get_port_data(
    port_name: Optional[str] = Query(
        default=None,
        description="Filter by specific port name",
    ),
    db: Session = Depends(get_db),
):
    """
    Fetch port constraint and congestion status.
    """
    stmt = select(PortData).order_by(PortData.port_name.asc())
    if port_name:
        stmt = stmt.where(PortData.port_name == port_name)

    results = db.scalars(stmt).all()
    return results
