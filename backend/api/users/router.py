from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import (
    ForumReply,
    ForumThread,
    Notification,
    Tool,
    ToolVote,
    User,
)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    tool_count: int


class UpdateProfile(BaseModel):
    display_name: str | None = None
    bio: str | None = None


@router.get("/{username}")
async def get_user_profile(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == username).options(selectinload(User.tools))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    active_tools = [t for t in user.tools if t.is_active]
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "tools": [
            {
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "language": t.language,
                "created_at": t.created_at.isoformat(),
            }
            for t in active_tools
        ],
    }


@router.patch("/me")
async def update_profile(
    body: UpdateProfile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    await db.commit()
    return {"status": "updated"}


@router.get("/me/data")
async def download_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download all user data as JSON (GDPR/CCPA data export)."""
    # Tools with tags
    tools_result = await db.execute(
        select(Tool)
        .where(Tool.author_id == user.id)
        .options(selectinload(Tool.tags))
    )
    tools = tools_result.scalars().all()

    # Forum replies
    replies_result = await db.execute(
        select(ForumReply).where(ForumReply.author_id == user.id)
    )
    replies = replies_result.scalars().all()

    # Votes
    votes_result = await db.execute(
        select(ToolVote).where(ToolVote.user_id == user.id)
    )
    votes = votes_result.scalars().all()

    # Notifications
    notifs_result = await db.execute(
        select(Notification).where(Notification.user_id == user.id)
    )
    notifications = notifs_result.scalars().all()

    data = {
        "profile": {
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "bio": user.bio,
            "created_at": user.created_at.isoformat(),
        },
        "tools": [
            {
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "problem_statement": t.problem_statement,
                "repo_url": t.repo_url,
                "license": t.license,
                "language": t.language,
                "is_active": t.is_active,
                "tags": [tag.tag for tag in t.tags],
                "created_at": t.created_at.isoformat(),
            }
            for t in tools
        ],
        "forum_replies": [
            {
                "id": str(r.id),
                "thread_id": str(r.thread_id),
                "body": r.body,
                "created_at": r.created_at.isoformat(),
            }
            for r in replies
        ],
        "votes": [
            {
                "tool_id": str(v.tool_id),
                "created_at": v.created_at.isoformat(),
            }
            for v in votes
        ],
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
    }

    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=centaur-tools-data.json"},
    )


@router.delete("/me")
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete account and anonymize content (GDPR/CCPA right to erasure)."""
    user_id = user.id

    # Replace all their forum replies with "[deleted]"
    await db.execute(
        update(ForumReply)
        .where(ForumReply.author_id == user_id)
        .values(body="[deleted]")
    )

    # Anonymize their forum threads (set title/body to indicate deleted user)
    await db.execute(
        update(ForumThread)
        .where(ForumThread.author_id == user_id)
        .values(body="[deleted]")
    )

    # Deactivate all their tools
    await db.execute(
        update(Tool)
        .where(Tool.author_id == user_id)
        .values(is_active=False)
    )

    # Delete all their votes
    await db.execute(
        delete(ToolVote).where(ToolVote.user_id == user_id)
    )

    # Delete all their notifications
    await db.execute(
        delete(Notification).where(Notification.user_id == user_id)
    )

    # Delete the user record
    await db.delete(user)
    await db.commit()

    return {"status": "account deleted"}


@router.get("/me/starred")
async def get_starred_tools(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tool)
        .join(ToolVote, ToolVote.tool_id == Tool.id)
        .where(ToolVote.user_id == user.id, Tool.is_active == True)
        .options(selectinload(Tool.tags))
        .order_by(ToolVote.created_at.desc())
    )
    tools = result.scalars().all()
    return {
        "tools": [
            {
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "language": t.language,
                "tags": [tag.tag for tag in t.tags],
                "created_at": t.created_at.isoformat(),
            }
            for t in tools
        ]
    }
