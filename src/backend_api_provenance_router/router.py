from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.dependencies import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Notification, PriorArtNomination, PriorArtVote, Tool, User

router = APIRouter(prefix="/api/prior-art", tags=["provenance"])


class NominationRequest(BaseModel):
    tool_slug: str
    platform: str
    platform_feature: str
    evidence: str


@router.get("/")
async def list_prior_art(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PriorArtNomination)
        .where(PriorArtNomination.confirmed == True)
        .options(selectinload(PriorArtNomination.tool), selectinload(PriorArtNomination.nominator))
        .order_by(PriorArtNomination.confirmed_at.desc())
    )
    nominations = result.scalars().all()
    return {
        "prior_art": [
            {
                "id": str(n.id),
                "tool": {"slug": n.tool.slug, "name": n.tool.name},
                "platform": n.platform,
                "platform_feature": n.platform_feature,
                "evidence": n.evidence,
                "nominated_by": n.nominator.username,
                "confirmed_at": n.confirmed_at.isoformat() if n.confirmed_at else None,
                "vote_count": len(n.votes),
            }
            for n in nominations
        ]
    }


@router.get("/pending")
async def list_pending(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PriorArtNomination)
        .where(PriorArtNomination.confirmed == False)
        .options(
            selectinload(PriorArtNomination.tool),
            selectinload(PriorArtNomination.nominator),
            selectinload(PriorArtNomination.votes),
        )
        .order_by(PriorArtNomination.created_at.desc())
    )
    nominations = result.scalars().all()
    return {
        "pending": [
            {
                "id": str(n.id),
                "tool": {"slug": n.tool.slug, "name": n.tool.name},
                "platform": n.platform,
                "platform_feature": n.platform_feature,
                "evidence": n.evidence,
                "nominated_by": n.nominator.username,
                "vote_count": len(n.votes),
                "threshold": settings.prior_art_vote_threshold,
                "created_at": n.created_at.isoformat(),
            }
            for n in nominations
        ]
    }


@router.post("/nominate")
async def nominate(
    body: NominationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tool).where(Tool.slug == body.tool_slug, Tool.is_active == True)
    )
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    nomination = PriorArtNomination(
        tool_id=tool.id,
        platform=body.platform,
        platform_feature=body.platform_feature,
        evidence=body.evidence,
        nominated_by=user.id,
    )
    db.add(nomination)

    # Notify tool author
    if tool.author_id != user.id:
        db.add(Notification(
            user_id=tool.author_id,
            type="prior_art_nomination",
            title=f"Prior Art nomination for {tool.name}",
            body=f"{user.username} nominated {tool.name} as prior art for {body.platform}'s {body.platform_feature}",
            data={"nomination_id": str(nomination.id), "tool_slug": tool.slug},
        ))

    await db.commit()
    return {"id": str(nomination.id), "status": "nominated"}


@router.post("/{nomination_id}/vote")
async def vote_on_nomination(
    nomination_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    nom_uuid = uuid.UUID(nomination_id)
    result = await db.execute(
        select(PriorArtNomination)
        .where(PriorArtNomination.id == nom_uuid)
        .options(selectinload(PriorArtNomination.votes), selectinload(PriorArtNomination.tool))
    )
    nomination = result.scalar_one_or_none()
    if not nomination:
        raise HTTPException(status_code=404, detail="Nomination not found")
    if nomination.confirmed:
        return {"status": "already_confirmed"}

    existing = await db.execute(
        select(PriorArtVote).where(
            PriorArtVote.nomination_id == nom_uuid,
            PriorArtVote.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_voted"}

    db.add(PriorArtVote(nomination_id=nom_uuid, user_id=user.id))
    await db.flush()

    # Check threshold
    vote_count = (await db.execute(
        select(func.count()).where(PriorArtVote.nomination_id == nom_uuid)
    )).scalar()

    if vote_count >= settings.prior_art_vote_threshold:
        nomination.confirmed = True
        nomination.confirmed_at = datetime.now(timezone.utc)

        # Notify tool author
        db.add(Notification(
            user_id=nomination.tool.author_id,
            type="prior_art_confirmed",
            title=f"Prior Art confirmed: {nomination.tool.name}",
            body=f"The community confirmed {nomination.tool.name} as prior art for {nomination.platform}'s {nomination.platform_feature}",
            data={"nomination_id": str(nomination.id), "tool_slug": nomination.tool.slug},
        ))

    await db.commit()
    return {
        "status": "voted",
        "vote_count": vote_count,
        "confirmed": nomination.confirmed,
    }
