"""Notification routes for ArborAura Market."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Notification, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "related_id": n.related_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.put("/{notif_id}/read")
def mark_read(
    notif_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == user.id).first()
    if n:
        n.is_read = 1
        db.commit()
    return {"status": "ok"}


@router.put("/read-all")
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == 0).update(
        {"is_read": 1}
    )
    db.commit()
    return {"status": "ok"}


@router.get("/unread-count")
def unread_notification_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == 0).count()
    return {"unread": count}
