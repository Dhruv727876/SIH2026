from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models.market_data import MarketData
from schemas.market_data import MarketDataCreate, MarketDataResponse

router = APIRouter(prefix="/api/v1/market-data", tags=["Market Data"])


@router.post(
    "",
    response_model=MarketDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a market data telemetry record",
)
def create_market_data(
    payload: MarketDataCreate,
    db: Session = Depends(get_db),
):
    """
    Ingest a new time-series market data point (e.g. BCI, BPI, BUNKER_SIN, USD_INR).
    """
    db_item = MarketData(
        timestamp=payload.timestamp,
        index_name=payload.index_name,
        value=payload.value,
        currency=payload.currency,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk ingest multiple market data telemetry records in a single transaction",
)
def create_market_data_bulk(
    payload: List[MarketDataCreate],
    db: Session = Depends(get_db),
):
    """
    High-performance bulk ingestion of time-series market records.
    """
    items = [
        MarketData(
            timestamp=p.timestamp,
            index_name=p.index_name,
            value=p.value,
            currency=p.currency,
        )
        for p in payload
    ]
    db.bulk_save_objects(items)
    db.commit()
    return {"status": "success", "inserted": len(items)}


@router.get(
    "",
    response_model=List[MarketDataResponse],
    summary="Retrieve latest market data records",
)
def get_market_data(
    index_name: Optional[str] = Query(
        default=None,
        description="Filter by index name (e.g. 'BCI', 'BPI', 'BUNKER_SIN')",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of records to return",
    ),
    db: Session = Depends(get_db),
):
    """
    Fetch market data records ordered by timestamp descending.
    """
    stmt = select(MarketData).order_by(MarketData.timestamp.desc())

    if index_name:
        stmt = stmt.where(MarketData.index_name == index_name)

    stmt = stmt.limit(limit)
    results = db.scalars(stmt).all()
    return results
