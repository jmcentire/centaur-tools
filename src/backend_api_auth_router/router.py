import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import User

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


