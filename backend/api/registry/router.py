import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user, get_optional_user
from ..database import get_db
from ..models import (
    ForumCategory,
    ForumReply,
    ForumThread,
    ForkLink,
    Notification,
    ProximityLink,
    Tool,
    ToolEmbedding,
    ToolTag,
    ToolVote,
    User,
)
from ..proximity.service import scan_proximity

router = APIRouter(prefix="/api/tools", tags=["registry"])


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


class ToolSubmission(BaseModel):
    name: str
    description: str
    problem_statement: str
    repo_url: str
    license: str = "MIT"
    language: str | None = None
    tags: list[str] = []
    fork_parent_slug: str | None = None

    @field_validator("license")
    @classmethod
    def must_be_mit(cls, v: str) -> str:
        if v.upper() != "MIT":
            raise ValueError(
                "centaur.tools requires MIT license. "
                "The social contract is: everything forkable, stealable, buildable-upon. "
                "Cite your parents. MIT is the only license that guarantees this."
            )
        return "MIT"


class ToolUpdate(BaseModel):
    description: str | None = None
    problem_statement: str | None = None
    repo_url: str | None = None
    language: str | None = None
    tags: list[str] | None = None


@router.get("/")
async def list_tools(
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    query = select(Tool).where(Tool.is_active == True).order_by(Tool.created_at.desc())
    if tag:
        query = query.join(ToolTag).where(ToolTag.tag == tag)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.options(selectinload(Tool.tags), selectinload(Tool.author))
    result = await db.execute(query)
    tools = result.scalars().all()

    # Get vote counts
    tool_ids = [t.id for t in tools]
    vote_counts = {}
    if tool_ids:
        vc = await db.execute(
            select(ToolVote.tool_id, func.count())
            .where(ToolVote.tool_id.in_(tool_ids))
            .group_by(ToolVote.tool_id)
        )
        vote_counts = dict(vc.all())

    # Get current user's votes
    user_votes = set()
    if user and tool_ids:
        uv = await db.execute(
            select(ToolVote.tool_id).where(
                ToolVote.user_id == user.id,
                ToolVote.tool_id.in_(tool_ids),
            )
        )
        user_votes = {row[0] for row in uv.all()}

    return {
        "tools": [
            {
                "slug": t.slug,
                "name": t.name,
                "description": t.description,
                "problem_statement": t.problem_statement,
                "language": t.language,
                "tags": [tag.tag for tag in t.tags],
                "author": {"username": t.author.username, "avatar_url": t.author.avatar_url},
                "vote_count": vote_counts.get(t.id, 0),
                "user_voted": t.id in user_votes,
                "created_at": t.created_at.isoformat(),
            }
            for t in tools
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/{slug}")
async def get_tool(slug: str, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    result = await db.execute(
        select(Tool)
        .where(Tool.slug == slug, Tool.is_active == True)
        .options(selectinload(Tool.tags), selectinload(Tool.author))
    )
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Vote count
    vc = await db.execute(select(func.count()).where(ToolVote.tool_id == tool.id))
    vote_count = vc.scalar()

    # User's vote
    user_voted = False
    if user:
        uv = await db.execute(
            select(ToolVote).where(ToolVote.tool_id == tool.id, ToolVote.user_id == user.id)
        )
        user_voted = uv.scalar_one_or_none() is not None

    # Proximity neighbors
    neighbors = []
    prox_q = await db.execute(
        select(ProximityLink, Tool)
        .join(Tool, (Tool.id == ProximityLink.tool_b_id) | (Tool.id == ProximityLink.tool_a_id))
        .where(
            ((ProximityLink.tool_a_id == tool.id) | (ProximityLink.tool_b_id == tool.id)),
            Tool.id != tool.id,
            Tool.is_active == True,
        )
        .order_by(ProximityLink.similarity.desc())
        .limit(10)
    )
    for link, neighbor in prox_q.all():
        neighbors.append({
            "slug": neighbor.slug,
            "name": neighbor.name,
            "similarity": link.similarity,
        })

    # Fork lineage
    forks = {"parents": [], "children": []}
    parent_q = await db.execute(
        select(Tool).join(ForkLink, ForkLink.parent_id == Tool.id).where(ForkLink.child_id == tool.id)
    )
    for parent in parent_q.scalars():
        forks["parents"].append({"slug": parent.slug, "name": parent.name})

    child_q = await db.execute(
        select(Tool).join(ForkLink, ForkLink.child_id == Tool.id).where(ForkLink.parent_id == tool.id)
    )
    for child in child_q.scalars():
        forks["children"].append({"slug": child.slug, "name": child.name})

    # Discussion thread
    discussion = None
    thread_q = await db.execute(
        select(ForumThread)
        .where(ForumThread.tool_id == tool.id)
        .options(selectinload(ForumThread.replies).selectinload(ForumReply.author))
    )
    thread = thread_q.scalar_one_or_none()
    if thread:
        discussion = {
            "thread_id": str(thread.id),
            "reply_count": thread.reply_count,
            "replies": [
                {
                    "id": str(r.id),
                    "author": {"username": r.author.username, "avatar_url": r.author.avatar_url},
                    "body": r.body,
                    "created_at": r.created_at.isoformat(),
                }
                for r in sorted(thread.replies, key=lambda r: r.created_at)
            ],
        }

    return {
        "slug": tool.slug,
        "name": tool.name,
        "description": tool.description,
        "problem_statement": tool.problem_statement,
        "repo_url": tool.repo_url,
        "license": tool.license,
        "language": tool.language,
        "tags": [tag.tag for tag in tool.tags],
        "author": {
            "username": tool.author.username,
            "display_name": tool.author.display_name,
            "avatar_url": tool.author.avatar_url,
        },
        "vote_count": vote_count,
        "user_voted": user_voted,
        "neighbors": neighbors,
        "forks": forks,
        "discussion": discussion,
        "created_at": tool.created_at.isoformat(),
        "updated_at": tool.updated_at.isoformat(),
    }


async def verify_repo_ownership(repo_url: str, username: str) -> bool:
    """Verify the GitHub user owns or has access to the repo."""
    import re
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+)/?', repo_url)
    if not match:
        return True  # Non-GitHub repos pass (can't verify)

    repo_owner = match.group(1).lower()
    if repo_owner == username.lower():
        return True  # Owner matches

    # Check if user is a collaborator via GitHub API (public endpoint)
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            # Check if repo exists and user is listed as contributor
            resp = await client.get(
                f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}",
                headers={"Accept": "application/json"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                repo_data = resp.json()
                # If it's an org repo, check contributors
                if repo_data.get("organization"):
                    collab_resp = await client.get(
                        f"https://api.github.com/repos/{match.group(1)}/{match.group(2)}/collaborators/{username}",
                        headers={"Accept": "application/json"},
                        timeout=5.0,
                    )
                    return collab_resp.status_code == 204
    except Exception:
        pass

    return False


@router.post("/")
async def submit_tool(
    body: ToolSubmission,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify repo ownership
    if not await verify_repo_ownership(body.repo_url, user.username):
        raise HTTPException(
            status_code=403,
            detail=f"The repository {body.repo_url} does not appear to belong to your GitHub account ({user.username}). "
                   "You can only register tools from repositories you own or have collaborator access to."
        )

    slug = slugify(body.name)
    existing = await db.execute(select(Tool).where(Tool.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    tool = Tool(
        slug=slug,
        name=body.name,
        description=body.description,
        problem_statement=body.problem_statement,
        repo_url=body.repo_url,
        license=body.license,
        language=body.language,
        author_id=user.id,
    )
    db.add(tool)
    await db.flush()

    for tag_name in body.tags[:20]:
        db.add(ToolTag(tool_id=tool.id, tag=tag_name.lower().strip()))

    # Fork lineage
    if body.fork_parent_slug:
        parent_result = await db.execute(
            select(Tool).where(Tool.slug == body.fork_parent_slug, Tool.is_active == True)
        )
        parent = parent_result.scalar_one_or_none()
        if parent:
            db.add(ForkLink(parent_id=parent.id, child_id=tool.id))
            db.add(Notification(
                user_id=parent.author_id,
                type="fork",
                title=f"{user.username} forked {parent.name}",
                body=f"New fork: {tool.name}",
                data={"tool_slug": tool.slug, "parent_slug": parent.slug},
            ))

    # Auto-create forum topic in "Show & Tell"
    show_tell = await db.execute(
        select(ForumCategory).where(ForumCategory.slug == "show-and-tell")
    )
    category = show_tell.scalar_one_or_none()
    if category:
        thread = ForumThread(
            tool_id=tool.id,
            category_id=category.id,
            author_id=user.id,
            title=f"{body.name} — {body.description[:200]}",
            body=f"**{body.name}** has been registered on centaur.tools.\n\n"
                 f"**Problem:** {body.problem_statement}\n\n"
                 f"**Repo:** {body.repo_url}\n\n"
                 f"Discuss this tool, share feedback, or connect with the builder.",
        )
        db.add(thread)

    await db.commit()
    await db.refresh(tool)

    # Trigger proximity scan (async, best-effort)
    try:
        await scan_proximity(tool, db)
    except Exception:
        pass  # Don't fail submission if proximity scan fails

    return {"slug": tool.slug, "status": "created"}


@router.patch("/{slug}")
async def update_tool(
    slug: str,
    body: ToolUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.slug == slug, Tool.is_active == True))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    if tool.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not the owner")

    if body.description is not None:
        tool.description = body.description
    if body.problem_statement is not None:
        tool.problem_statement = body.problem_statement
    if body.repo_url is not None:
        tool.repo_url = body.repo_url
    if body.language is not None:
        tool.language = body.language
    if body.tags is not None:
        await db.execute(
            ToolTag.__table__.delete().where(ToolTag.tool_id == tool.id)
        )
        for tag_name in body.tags[:20]:
            db.add(ToolTag(tool_id=tool.id, tag=tag_name.lower().strip()))

    await db.commit()

    # Re-scan proximity if problem statement changed
    if body.problem_statement is not None:
        try:
            await scan_proximity(tool, db)
        except Exception:
            pass

    return {"slug": tool.slug, "status": "updated"}


@router.delete("/{slug}")
async def deactivate_tool(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tool).where(Tool.slug == slug))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    if tool.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not the owner")

    tool.is_active = False
    await db.commit()
    return {"status": "deactivated"}
