from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aquaguard.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_default_token() -> str:
    return os.getenv("DEMO_TOKEN", "demo-token")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def user_session_expired(created_at: datetime, expires_at: Optional[datetime]) -> bool:
    if expires_at is None:
        return False
    return datetime.now(timezone.utc) > expires_at


with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
