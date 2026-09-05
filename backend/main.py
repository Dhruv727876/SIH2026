import logging
import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # Ensures all ORM models are registered with Base.metadata
from routers.health import router as health_router
from routers.market_data import router as market_data_router
from routers.port_data import router as port_data_router
from routers.forecasts import router as forecasts_router
from routers.optimization import router as optimization_router
from routers.disruptions import router as disruptions_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("freight-dss")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and cleanup."""
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(
            "Could not connect to database on startup (container may still be starting). "
            f"Error: {e}"
        )
    yield
    logger.info("Shutting down Freight DSS backend service.")


app = FastAPI(
    title="Freight DSS Backend API",
    description="Decision Support System for Intelligent Freight Forecasting and Optimized Vessel Chartering",
    version="1.0.0",
    lifespan=lifespan,
)

# Dynamic CORS setup for frontend communication
origins_env = os.getenv("ALLOWED_ORIGINS", "*")
if not origins_env or origins_env.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    if not allowed_origins:
        allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(market_data_router)
app.include_router(port_data_router)
app.include_router(forecasts_router)
app.include_router(optimization_router)
app.include_router(disruptions_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Freight DSS API. Visit /docs for OpenAPI documentation.",
        "health": "/api/v1/health",
        "market_data": "/api/v1/market-data",
        "port_data": "/api/v1/port-data",
        "forecasts": "/api/v1/forecasts/{index_name}",
        "optimize": "/api/v1/optimize",
        "disruptions": "/api/v1/disruptions",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
