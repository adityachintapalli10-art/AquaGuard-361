from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserSession

security = HTTPBearer(auto_error=False)


def get_current_user_from_token(token: str, db: Session) -> User | None:
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None
    return db.query(User).filter(User.id == session.user_id).first()


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_current_user_from_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    return get_current_user_from_token(credentials.credentials, db)
