from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify backend service availability."""
    return {"status": "ok", "service": "freight-dss-backend"}
