from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base

# SQLite DB file in project root: ./ptqa.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./ptqa.db"

# check_same_thread=False is required for SQLite + FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Import all models and create tables.
    Call this once on application startup.
    """
    # Import models so they are registered with Base.metadata
    from app.db import models_decisions  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency to get a DB session in FastAPI routes.
    Usage:
        db = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
