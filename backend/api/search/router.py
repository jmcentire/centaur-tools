from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..models import Tool, ToolEmbedding, ToolTag, ToolVote

router = APIRouter(prefix="/api/search", tags=["search"])


async def get_embedding(text_input: str) -> list[float] | None:
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        result = client.models.embed_content(
            model="models/text-embedding-004",
            contents=text_input,
        )
        return result.embeddings[0].values
    except Exception:
        return None


@router.get("/")
async def search_tools(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid", pattern="^(keyword|semantic|hybrid)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    results = []
    tool_scores: dict[str, float] = {}

    if mode in ("keyword", "hybrid"):
        # Full-text search
        fts_query = (
            select(Tool, func.ts_rank(Tool.search_vector, func.plainto_tsquery("english", q)).label("rank"))
            .where(
                Tool.is_active == True,
                Tool.search_vector.op("@@")(func.plainto_tsquery("english", q)),
            )
            .order_by(text("rank DESC"))
            .limit(per_page * 2)
        )
        fts_result = await db.execute(fts_query)
        for tool, rank in fts_result.all():
            tool_scores[str(tool.id)] = float(rank)

    if mode in ("semantic", "hybrid"):
        embedding = await get_embedding(q)
        if embedding:
            # Vector similarity search
            vec_query = (
                select(
                    ToolEmbedding.tool_id,
                    (1 - ToolEmbedding.embedding.cosine_distance(embedding)).label("similarity"),
                )
                .order_by(text("similarity DESC"))
                .limit(per_page * 2)
            )
            vec_result = await db.execute(vec_query)
            for tool_id, similarity in vec_result.all():
                key = str(tool_id)
                existing = tool_scores.get(key, 0)
                tool_scores[key] = max(existing, float(similarity))

    # Tag matching — always include tools that have a matching tag
    tag_query = q.lower().strip()
    tag_matches = await db.execute(
        select(Tool)
        .join(ToolTag)
        .where(Tool.is_active == True, ToolTag.tag == tag_query)
        .limit(per_page)
    )
    for tool in tag_matches.scalars():
        key = str(tool.id)
        if key not in tool_scores:
            tool_scores[key] = 0.5  # Below FTS rank but above fallback

    if not tool_scores:
        # Fallback: prefix match on name
        fallback = await db.execute(
            select(Tool)
            .where(Tool.is_active == True, Tool.name.ilike(f"%{q}%"))
            .limit(per_page)
        )
        for tool in fallback.scalars():
            tool_scores[str(tool.id)] = 0.1

    # Sort by score, paginate
    sorted_ids = sorted(tool_scores, key=tool_scores.get, reverse=True)
    page_ids = sorted_ids[(page - 1) * per_page : page * per_page]

    if not page_ids:
        return {"tools": [], "total": 0, "page": page, "per_page": per_page}

    import uuid as _uuid

    uuid_ids = [_uuid.UUID(tid) for tid in page_ids]
    tools_q = await db.execute(
        select(Tool)
        .where(Tool.id.in_(uuid_ids), Tool.is_active == True)
        .options(selectinload(Tool.tags), selectinload(Tool.author))
    )
    tools_map = {str(t.id): t for t in tools_q.scalars()}

    # Vote counts
    vote_q = await db.execute(
        select(ToolVote.tool_id, func.count())
        .where(ToolVote.tool_id.in_(uuid_ids))
        .group_by(ToolVote.tool_id)
    )
    vote_counts = dict(vote_q.all())

    tools_out = []
    for tid in page_ids:
        t = tools_map.get(tid)
        if not t:
            continue
        tools_out.append({
            "slug": t.slug,
            "name": t.name,
            "description": t.description,
            "problem_statement": t.problem_statement,
            "language": t.language,
            "tags": [tag.tag for tag in t.tags],
            "author": {"username": t.author.username, "avatar_url": t.author.avatar_url},
            "vote_count": vote_counts.get(t.id, 0),
            "score": round(tool_scores[tid], 4),
            "created_at": t.created_at.isoformat(),
        })

    return {
        "tools": tools_out,
        "total": len(tool_scores),
        "page": page,
        "per_page": per_page,
    }
