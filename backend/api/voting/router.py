from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import Tool, ToolVote, User

router = APIRouter(prefix="/api/tools", tags=["voting"])


@router.post("/{slug}/vote")
async def vote_useful(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.slug == slug, Tool.is_active == True))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    existing = await db.execute(
        select(ToolVote).where(ToolVote.tool_id == tool.id, ToolVote.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        return {"status": "already_voted"}

    db.add(ToolVote(tool_id=tool.id, user_id=user.id))
    await db.commit()

    count = (await db.execute(select(func.count()).where(ToolVote.tool_id == tool.id))).scalar()
    return {"status": "voted", "vote_count": count}


@router.delete("/{slug}/vote")
async def remove_vote(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.slug == slug, Tool.is_active == True))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    existing = await db.execute(
        select(ToolVote).where(ToolVote.tool_id == tool.id, ToolVote.user_id == user.id)
    )
    vote = existing.scalar_one_or_none()
    if not vote:
        return {"status": "not_voted"}

    await db.delete(vote)
    await db.commit()

    count = (await db.execute(select(func.count()).where(ToolVote.tool_id == tool.id))).scalar()
    return {"status": "removed", "vote_count": count}
