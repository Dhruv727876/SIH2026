import logging
import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/freight_dss"
)

# Standardize postgres:// to postgresql:// for SQLAlchemy compatibility (common in Neon/Supabase/Render)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def init_engine(url: str):
    """Initializes SQLAlchemy engine with auto-fallback to SQLite if PostgreSQL is unavailable."""
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

    try:
        # Standardize connection scheme if needed
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        eng = create_engine(
            url,
            echo=False,
            pool_pre_ping=True,   # Reconnects automatically on dropped/idle cloud connections
            pool_recycle=300,       # Recycles connections every 5 minutes to prevent cloud timeout
            pool_size=10,
            max_overflow=20,
        )
        # Test connection
        with eng.connect() as conn:
            logger.info("Database connection established successfully.")
        return eng
    except Exception as e:
        logger.warning(
            f"PostgreSQL connection failed ({e}). "
            "Falling back to local SQLite database (sqlite:///./freight_dss.db) for zero-downtime execution."
        )
        sqlite_url = "sqlite:///./freight_dss.db"
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )


engine = init_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing request-scoped database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
