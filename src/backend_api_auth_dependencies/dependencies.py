import uuid

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from .router import decode_jwt


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    session: str | None = Cookie(default=None),
) -> User:
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt(session)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    session: str | None = Cookie(default=None),
) -> User | None:
    if not session:
        return None
    try:
        payload = decode_jwt(session)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
