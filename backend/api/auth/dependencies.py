"""Auth dependencies — accept either session cookie or Bearer token.

Two auth paths are equally valid for any endpoint that does
`user: User = Depends(get_current_user)`:

  1. **Session cookie** (existing): browser flow via GitHub OAuth → JWT in
     a `session` cookie.
  2. **API token** (new): `Authorization: Bearer cnt_<...>` header, where
     the token was issued by `POST /api/auth/tokens` while authenticated
     via path 1.

Path 2 makes the registry agent-friendly: a CLI / script / agent can
submit tools, vote, comment, etc. without a browser session.
"""

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ApiToken, User
from .router import decode_jwt


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _user_from_bearer(db: AsyncSession, raw_token: str) -> User | None:
    """Validate a bearer token and return the owning user, or None."""
    if not raw_token.startswith("cnt_"):
        return None
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ApiToken, User)
        .join(User, User.id == ApiToken.user_id)
        .where(ApiToken.token_hash == token_hash)
        .where(ApiToken.revoked_at.is_(None))
    )
    row = result.first()
    if not row:
        return None
    token, user = row
    if token.expires_at is not None and token.expires_at < now:
        return None
    # Best-effort touch of last_used_at; failure here shouldn't block auth.
    try:
        await db.execute(
            update(ApiToken).where(ApiToken.id == token.id).values(last_used_at=now)
        )
        await db.commit()
    except Exception:
        await db.rollback()
    return user


async def _user_from_session(db: AsyncSession, session: str) -> User | None:
    try:
        payload = decode_jwt(session)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> User:
    # Bearer token takes precedence if present (more explicit signal).
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
        user = await _user_from_bearer(db, raw)
        if user:
            return user
        raise HTTPException(status_code=401, detail="Invalid or expired API token")

    if session:
        user = await _user_from_session(db, session)
        if user:
            return user
        raise HTTPException(status_code=401, detail="Invalid session")

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> User | None:
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
        user = await _user_from_bearer(db, raw)
        if user:
            return user
        # Don't error in optional path; just fall through.

    if session:
        return await _user_from_session(db, session)

    return None
