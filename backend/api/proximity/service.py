import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import Notification, ProximityLink, Tool, ToolEmbedding
from ..search.router import get_embedding


async def scan_proximity(tool: Tool, db: AsyncSession) -> list[dict]:
    """Generate embedding for tool's problem statement and find neighbors."""
    embedding = await get_embedding(tool.problem_statement)
    if not embedding:
        return []

    # Upsert embedding
    existing = await db.execute(
        select(ToolEmbedding).where(ToolEmbedding.tool_id == tool.id)
    )
    emb = existing.scalar_one_or_none()
    if emb:
        emb.embedding = embedding
    else:
        db.add(ToolEmbedding(tool_id=tool.id, embedding=embedding))
    await db.flush()

    # Find neighbors
    vec_query = (
        select(
            ToolEmbedding.tool_id,
            (1 - ToolEmbedding.embedding.cosine_distance(embedding)).label("similarity"),
        )
        .where(ToolEmbedding.tool_id != tool.id)
        .order_by(text("similarity DESC"))
        .limit(20)
    )
    results = await db.execute(vec_query)
    neighbors = []

    for neighbor_tool_id, similarity in results.all():
        if similarity < settings.proximity_threshold:
            continue

        # Create proximity link (canonical ordering)
        a_id, b_id = sorted([tool.id, neighbor_tool_id])
        existing_link = await db.execute(
            select(ProximityLink).where(
                ProximityLink.tool_a_id == a_id,
                ProximityLink.tool_b_id == b_id,
            )
        )
        if not existing_link.scalar_one_or_none():
            db.add(ProximityLink(tool_a_id=a_id, tool_b_id=b_id, similarity=float(similarity)))

            # Notify the neighbor's author
            neighbor_tool = await db.execute(
                select(Tool).where(Tool.id == neighbor_tool_id)
            )
            nt = neighbor_tool.scalar_one_or_none()
            if nt and nt.author_id != tool.author_id:
                db.add(Notification(
                    user_id=nt.author_id,
                    type="proximity",
                    title=f"New neighbor: {tool.name}",
                    body=f"{tool.name} is working on a similar problem to {nt.name}",
                    data={
                        "tool_slug": tool.slug,
                        "neighbor_slug": nt.slug,
                        "similarity": round(float(similarity), 3),
                    },
                ))

        neighbors.append({
            "tool_id": str(neighbor_tool_id),
            "similarity": round(float(similarity), 3),
        })

    await db.commit()
    return neighbors
