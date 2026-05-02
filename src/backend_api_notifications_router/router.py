import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": n.data,
                "read": n.read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]
    }


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (await db.execute(
        select(func.count()).where(
            Notification.user_id == user.id,
            Notification.read == False,
        )
    )).scalar()
    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    nid = uuid.UUID(notification_id)
    result = await db.execute(
        select(Notification).where(Notification.id == nid, Notification.user_id == user.id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    await db.commit()
    return {"status": "read"}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return {"status": "all_read"}
