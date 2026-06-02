"""Chat / messaging routes for ArborAura Market.
Supports conversations between buyers and sellers with read receipts.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, Listing, Message, Notification, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Schemas ──

class SendMessageRequest(BaseModel):
    conversation_id: Optional[int] = None
    listing_id: Optional[int] = None
    content: str


class ConversationResponse(BaseModel):
    id: int
    listing_id: int
    listing_title: str = ""
    listing_price: float = 0
    listing_image: str = ""
    buyer_id: int
    buyer_name: str = ""
    seller_id: int
    seller_name: str = ""
    subject: str
    is_buyer_read: int
    is_seller_read: int
    last_message: str = ""
    last_message_time: Optional[str] = None
    last_message_sender_id: Optional[int] = None
    unread_count: int = 0
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: str = ""
    content: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Routes ──

@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all conversations for the current user (as buyer or seller)."""
    convs = (
        db.query(Conversation)
        .filter((Conversation.buyer_id == user.id) | (Conversation.seller_id == user.id))
        .order_by(Conversation.last_message_at.desc())
        .all()
    )

    result = []
    for c in convs:
        listing = db.query(Listing).filter(Listing.id == c.listing_id).first()
        buyer = db.query(User).filter(User.id == c.buyer_id).first()
        seller = db.query(User).filter(User.id == c.seller_id).first()

        # Get last message
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .first()
        )

        # Count unread
        unread = 0
        if user.id == c.buyer_id and not c.is_buyer_read:
            unread = (
                db.query(Message)
                .filter(
                    Message.conversation_id == c.id,
                    Message.sender_id != user.id,
                )
                .count()
            )
        elif user.id == c.seller_id and not c.is_seller_read:
            unread = (
                db.query(Message)
                .filter(
                    Message.conversation_id == c.id,
                    Message.sender_id != user.id,
                )
                .count()
            )

        cr = ConversationResponse(
            id=c.id,
            listing_id=c.listing_id,
            listing_title=listing.title_fi if listing else "",
            listing_price=listing.price if listing else 0,
            listing_image="",
            buyer_id=c.buyer_id,
            buyer_name=buyer.full_name or (buyer.email.split("@")[0] if buyer else ""),
            seller_id=c.seller_id,
            seller_name=seller.full_name or (seller.email.split("@")[0] if seller else ""),
            subject=c.subject,
            is_buyer_read=c.is_buyer_read,
            is_seller_read=c.is_seller_read,
            last_message=last_msg.content if last_msg else "",
            last_message_time=last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None,
            last_message_sender_id=last_msg.sender_id if last_msg else None,
            unread_count=unread,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        result.append(cr)
    return result


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages in a conversation and mark as read."""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.buyer_id != user.id and conv.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not a participant in this conversation")

    # Mark as read
    if user.id == conv.buyer_id:
        conv.is_buyer_read = 1
    else:
        conv.is_seller_read = 1
    db.commit()

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    result = []
    for m in messages:
        sender = db.query(User).filter(User.id == m.sender_id).first()
        result.append(MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            sender_id=m.sender_id,
            sender_name=sender.full_name or (sender.email.split("@")[0] if sender else ""),
            content=m.content,
            created_at=m.created_at.isoformat() if m.created_at else None,
        ))
    return result


@router.post("/send")
def send_message(
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message. If conversation_id is given, use existing conversation.
    Otherwise create a new one with listing_id."""
    conv = None

    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.buyer_id != user.id and conv.seller_id != user.id:
            raise HTTPException(status_code=403, detail="Not a participant")
    elif req.listing_id:
        listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.user_id == user.id:
            raise HTTPException(status_code=400, detail="Cannot message yourself")

        # Check for existing conversation
        existing = (
            db.query(Conversation)
            .filter(
                Conversation.listing_id == req.listing_id,
                Conversation.buyer_id == user.id,
            )
            .first()
        )
        if existing:
            conv = existing
        else:
            conv = Conversation(
                listing_id=req.listing_id,
                buyer_id=user.id,
                seller_id=listing.user_id,
                subject=listing.title_fi or listing.title_en,
            )
            db.add(conv)
            db.flush()
    else:
        raise HTTPException(status_code=400, detail="Provide conversation_id or listing_id")

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        content=req.content,
    )
    db.add(msg)

    conv.last_message_at = datetime.utcnow()
    if user.id == conv.buyer_id:
        conv.is_seller_read = 0
    else:
        conv.is_buyer_read = 0
    db.commit()

    # Create notification for the recipient
    recipient_id = conv.seller_id if user.id == conv.buyer_id else conv.buyer_id
    notif = Notification(
        user_id=recipient_id,
        type="message",
        title="Uusi viesti / New message",
        message=f"{user.full_name or user.email.split('@')[0]}: {req.content[:100]}",
        related_id=conv.id,
    )
    db.add(notif)
    db.commit()

    return {"status": "ok", "conversation_id": conv.id, "message_id": msg.id}


@router.get("/unread-count")
def unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get total unread message count for the current user."""
    convs = (
        db.query(Conversation)
        .filter((Conversation.buyer_id == user.id) | (Conversation.seller_id == user.id))
        .all()
    )

    total = 0
    for c in convs:
        if user.id == c.buyer_id and not c.is_buyer_read:
            total += (
                db.query(Message)
                .filter(Message.conversation_id == c.id, Message.sender_id != user.id)
                .count()
            )
        elif user.id == c.seller_id and not c.is_seller_read:
            total += (
                db.query(Message)
                .filter(Message.conversation_id == c.id, Message.sender_id != user.id)
                .count()
            )

    return {"unread": total}
