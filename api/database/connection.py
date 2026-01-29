"""
Database connection and session management

Supports:
- SQLite (local development): sqlite:///./chartsense.db
- PostgreSQL (production): postgresql://user:pass@host:port/dbname
- Railway/Supabase/Neon: postgres:// URLs are auto-converted
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database URL - defaults to SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chartsense.db")

# Railway and some providers use 'postgres://' but SQLAlchemy needs 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite: need check_same_thread=False for FastAPI async
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
elif DATABASE_URL.startswith("postgresql"):
    # PostgreSQL: use connection pooling for production
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections after 30 min
        echo=False
    )
else:
    # Fallback for other databases
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes to get database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Call this on application startup.
    """
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
