import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import ApiToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def create_jwt(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.jwt_expiry_days),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    session: str | None = None,
) -> User:
    """Placeholder. Overridden in main.py with real cookie-based auth."""
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/login")
async def login():
    return RedirectResponse(
        f"{GITHUB_AUTHORIZE_URL}?client_id={settings.github_client_id}&scope=read:user user:email"
    )


@router.get("/callback")
async def callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        gh_user = user_resp.json()

    github_id = gh_user["id"]
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            github_id=github_id,
            username=gh_user["login"],
            display_name=gh_user.get("name"),
            email=gh_user.get("email"),
            avatar_url=gh_user.get("avatar_url"),
            bio=gh_user.get("bio"),
        )
        db.add(user)
    else:
        user.avatar_url = gh_user.get("avatar_url")
        user.display_name = gh_user.get("name")
        user.email = gh_user.get("email")

    await db.commit()
    await db.refresh(user)

    token = create_jwt(user.id)
    response = RedirectResponse(url=settings.frontend_url + "/dashboard")
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_expiry_days * 86400,
    )
    return response


@router.post("/logout")
async def logout():
    response = Response(status_code=204)
    response.delete_cookie("session")
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
    }


# ---- API tokens (programmatic / agent-friendly auth) ----

class TokenCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


def _generate_token() -> tuple[str, str, str]:
    """Returns (raw_token, token_hash, prefix). Raw token is shown once."""
    body = secrets.token_urlsafe(32).replace("-", "").replace("_", "")[:32]
    raw = f"cnt_{body}"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:12]  # cnt_ + first 8 chars
    return raw, token_hash, prefix


@router.post("/tokens", status_code=201)
async def create_api_token(
    body: TokenCreateBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a new API token for the authenticated user.

    Requires existing session-cookie auth (no chicken-and-egg with bearer auth
    on this specific endpoint — caller must already be a real logged-in user
    in a browser to mint a token).

    The raw token is returned ONLY in this response. Store it immediately;
    it cannot be retrieved later. Use as `Authorization: Bearer <token>` on
    all other endpoints.
    """
    raw, token_hash, prefix = _generate_token()
    expires_at = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    record = ApiToken(
        user_id=user.id, name=body.name, token_hash=token_hash,
        prefix=prefix, expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "id": str(record.id),
        "name": record.name,
        "token": raw,                      # shown ONCE
        "prefix": record.prefix,
        "created_at": record.created_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }


@router.get("/tokens")
async def list_api_tokens(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user.id)
        .where(ApiToken.revoked_at.is_(None))
        .order_by(ApiToken.created_at.desc())
    )
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "prefix": t.prefix,
            "created_at": t.created_at.isoformat(),
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        }
        for t in result.scalars().all()
    ]


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_api_token(
    token_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiToken).where(ApiToken.id == token_id).where(ApiToken.user_id == user.id)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    if token.revoked_at is None:
        await db.execute(
            update(ApiToken).where(ApiToken.id == token_id).values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
    return Response(status_code=204)


