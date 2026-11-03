"""SQLAlchemy database engine and session configuration."""

import time
from typing import Generator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Engine configuration supporting local SQLite and production PostgreSQL pooling
engine_kwargs = {
    "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL connection pooling
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE_SECONDS

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a thread-local SQLAlchemy session.

    Automatically rolls back uncommitted dirty transactions on unhandled
    exceptions before returning the connection to the pool.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connectivity(db_session: Optional[Session] = None) -> Tuple[bool, float, str]:
    """Execute a standard connection probe ('SELECT 1') and report latency in milliseconds.

    Returns:
        (is_connected: bool, latency_ms: float, dialect_name: str)
    """
    start_time = time.perf_counter()
    session = db_session if db_session is not None else SessionLocal()
    owns_session = db_session is None
    try:
        session.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        bind = session.get_bind()
        dialect_name = bind.dialect.name if bind else "unknown"
        return True, latency_ms, dialect_name
    except Exception as e:
        return False, 0.0, str(e)
    finally:
        if owns_session:
            session.close()


