from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserSession

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session_token(user: User, db: Session) -> str:
    token = secrets.token_urlsafe(32)
    session = UserSession(user_id=user.id, token=token, created_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    db.add(session)
    db.commit()
    return token


def get_user_from_token(token: str, db: Session) -> Optional[User]:
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None
    if session.expires_at and session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return db.query(User).filter(User.id == session.user_id).first()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_from_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    return get_user_from_token(credentials.credentials, db)
