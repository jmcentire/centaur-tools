from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import ForumCategory, ForumReply, ForumThread, ThreadVote, Tool, User

router = APIRouter(tags=["forum"])


class CreateThread(BaseModel):
    title: str
    body: str
    category_slug: str


class CreateReply(BaseModel):
    body: str



# --- Forum ---

@router.get("/api/forum/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ForumCategory).order_by(ForumCategory.sort_order)
    )
    categories = result.scalars().all()

    out = []
    for cat in categories:
        thread_count = (await db.execute(
            select(func.count()).where(ForumThread.category_id == cat.id)
        )).scalar()
        out.append({
            "slug": cat.slug,
            "name": cat.name,
            "description": cat.description,
            "thread_count": thread_count,
        })
    return {"categories": out}


from ..auth.dependencies import get_optional_user

@router.get("/api/forum/categories/{slug}")
async def list_threads(
    slug: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    result = await db.execute(select(ForumCategory).where(ForumCategory.slug == slug))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    total = (await db.execute(
        select(func.count()).where(ForumThread.category_id == category.id)
    )).scalar()

    threads_q = await db.execute(
        select(ForumThread)
        .where(ForumThread.category_id == category.id)
        .options(selectinload(ForumThread.author))
        .order_by(ForumThread.is_pinned.desc(), ForumThread.last_activity_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    threads = threads_q.scalars().all()

    # Vote counts for threads
    thread_ids = [t.id for t in threads]
    vote_counts = {}
    if thread_ids:
        vc = await db.execute(
            select(ThreadVote.thread_id, func.count())
            .where(ThreadVote.thread_id.in_(thread_ids))
            .group_by(ThreadVote.thread_id)
        )
        vote_counts = dict(vc.all())

    # User's thread votes
    user_thread_votes = set()
    if user and thread_ids:
        uv = await db.execute(
            select(ThreadVote.thread_id).where(
                ThreadVote.user_id == user.id,
                ThreadVote.thread_id.in_(thread_ids),
            )
        )
        user_thread_votes = {row[0] for row in uv.all()}

    return {
        "category": {"slug": category.slug, "name": category.name, "description": category.description},
        "threads": [
            {
                "id": str(t.id),
                "title": t.title,
                "author": {"username": t.author.username, "avatar_url": t.author.avatar_url},
                "reply_count": t.reply_count,
                "vote_count": vote_counts.get(t.id, 0),
                "user_voted": t.id in user_thread_votes,
                "is_pinned": t.is_pinned,
                "is_locked": t.is_locked,
                "last_activity_at": t.last_activity_at.isoformat(),
                "created_at": t.created_at.isoformat(),
            }
            for t in threads
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/api/forum/threads/{thread_id}")
async def get_thread(thread_id: str, db: AsyncSession = Depends(get_db)):
    import uuid

    tid = uuid.UUID(thread_id)
    result = await db.execute(
        select(ForumThread)
        .where(ForumThread.id == tid)
        .options(
            selectinload(ForumThread.author),
            selectinload(ForumThread.category),
            selectinload(ForumThread.replies).selectinload(ForumReply.author),
            selectinload(ForumThread.tool).selectinload(Tool.tags),
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Include tool data if this thread is linked to a tool
    from ..models import ToolVote
    tool_data = None
    if thread.tool and thread.tool.is_active:
        t = thread.tool
        vc = await db.execute(select(func.count()).where(ToolVote.tool_id == t.id))
        tool_data = {
            "slug": t.slug,
            "name": t.name,
            "description": t.description,
            "language": t.language,
            "tags": [tag.tag for tag in t.tags],
            "repo_url": t.repo_url,
            "vote_count": vc.scalar() or 0,
        }

    return {
        "id": str(thread.id),
        "title": thread.title,
        "body": thread.body,
        "category": {"slug": thread.category.slug, "name": thread.category.name},
        "author": {
            "username": thread.author.username,
            "display_name": thread.author.display_name,
            "avatar_url": thread.author.avatar_url,
        },
        "is_pinned": thread.is_pinned,
        "is_locked": thread.is_locked,
        "tool": tool_data,
        "replies": [
            {
                "id": str(r.id),
                "body": r.body,
                "author": {"username": r.author.username, "avatar_url": r.author.avatar_url},
                "created_at": r.created_at.isoformat(),
            }
            for r in sorted(thread.replies, key=lambda r: r.created_at)
        ],
        "created_at": thread.created_at.isoformat(),
    }


@router.post("/api/forum/threads")
async def create_thread(
    body: CreateThread,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ForumCategory).where(ForumCategory.slug == body.category_slug))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    thread = ForumThread(
        category_id=category.id,
        author_id=user.id,
        title=body.title,
        body=body.body,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return {"id": str(thread.id), "status": "created"}


@router.post("/api/forum/threads/{thread_id}/replies")
async def create_reply(
    thread_id: str,
    body: CreateReply,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    tid = uuid.UUID(thread_id)
    result = await db.execute(select(ForumThread).where(ForumThread.id == tid))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.is_locked:
        raise HTTPException(status_code=403, detail="Thread is locked")

    reply = ForumReply(thread_id=tid, author_id=user.id, body=body.body)
    db.add(reply)
    thread.reply_count += 1
    thread.last_activity_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": str(reply.id), "status": "created"}


class UpdateReply(BaseModel):
    body: str


@router.patch("/api/forum/replies/{reply_id}")
async def edit_reply(
    reply_id: str,
    body: UpdateReply,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    rid = _uuid.UUID(reply_id)
    result = await db.execute(select(ForumReply).where(ForumReply.id == rid))
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    if reply.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not the author")
    reply.body = body.body
    reply.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated"}


@router.delete("/api/forum/replies/{reply_id}")
async def delete_reply(
    reply_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    rid = _uuid.UUID(reply_id)
    result = await db.execute(
        select(ForumReply).where(ForumReply.id == rid).options(selectinload(ForumReply.thread))
    )
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    if reply.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not the author")
    reply.body = "[deleted]"
    reply.updated_at = datetime.now(timezone.utc)
    if reply.thread:
        reply.thread.reply_count = max(0, reply.thread.reply_count - 1)
    await db.commit()
    return {"status": "deleted"}


@router.post("/api/forum/threads/{thread_id}/vote")
async def vote_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    tid = _uuid.UUID(thread_id)
    result = await db.execute(select(ForumThread).where(ForumThread.id == tid))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    existing = await db.execute(
        select(ThreadVote).where(ThreadVote.thread_id == tid, ThreadVote.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        count = (await db.execute(select(func.count()).where(ThreadVote.thread_id == tid))).scalar()
        return {"status": "already_voted", "vote_count": count}

    db.add(ThreadVote(thread_id=tid, user_id=user.id))
    await db.commit()
    count = (await db.execute(select(func.count()).where(ThreadVote.thread_id == tid))).scalar()
    return {"status": "voted", "vote_count": count}


@router.delete("/api/forum/threads/{thread_id}/vote")
async def unvote_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    tid = _uuid.UUID(thread_id)
    existing = await db.execute(
        select(ThreadVote).where(ThreadVote.thread_id == tid, ThreadVote.user_id == user.id)
    )
    vote = existing.scalar_one_or_none()
    if not vote:
        count = (await db.execute(select(func.count()).where(ThreadVote.thread_id == tid))).scalar()
        return {"status": "not_voted", "vote_count": count}

    await db.delete(vote)
    await db.commit()
    count = (await db.execute(select(func.count()).where(ThreadVote.thread_id == tid))).scalar()
    return {"status": "removed", "vote_count": count}


