import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from routes.auth import get_current_user
from database import get_db
from models import User, Listing, SavedListing, Conversation, Message, Review, Notification, ListingReport, ContactSubmission, ListingView

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


@router.get("/export")
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. User Profile Data
    profile = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }

    # 2. User's Listings
    listings = []
    for l in db.query(Listing).filter(Listing.user_id == user.id).all():
        try:
            images_list = json.loads(l.images) if l.images else []
        except Exception:
            images_list = []
        listings.append({
            "id": l.id,
            "title_fi": l.title_fi,
            "title_en": l.title_en,
            "description": l.description,
            "condition": l.condition,
            "price": l.price,
            "location": l.location,
            "images": images_list,
            "boost_type": l.boost_type,
            "boost_expires": l.boost_expires.isoformat() if l.boost_expires else None,
            "status": l.status,
            "is_featured": l.is_featured,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        })

    # 3. User's Saved Listings (Favorites)
    saved_listings = []
    for sl in db.query(SavedListing).filter(SavedListing.user_id == user.id).all():
        listing = sl.listing
        saved_listings.append({
            "saved_at": sl.created_at.isoformat() if sl.created_at else None,
            "listing_id": sl.listing_id,
            "listing_title": (listing.title_fi or listing.title_en) if listing else "Unknown"
        })

    # 4. User's Conversations & Sent Messages
    conversations = []
    # Find all conversations where the user is either buyer or seller
    user_convs = db.query(Conversation).filter(
        (Conversation.buyer_id == user.id) | (Conversation.seller_id == user.id)
    ).all()
    
    for conv in user_convs:
        messages = []
        for msg in db.query(Message).filter(Message.conversation_id == conv.id).all():
            messages.append({
                "sender_id": msg.sender_id,
                "sender_name": msg.sender.full_name if msg.sender else "Deleted User",
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        conversations.append({
            "id": conv.id,
            "listing_id": conv.listing_id,
            "listing_title": (conv.listing.title_fi or conv.listing.title_en) if conv.listing else "Deleted Listing",
            "buyer_name": conv.buyer.full_name if conv.buyer else "Deleted User",
            "seller_name": conv.seller.full_name if conv.seller else "Deleted User",
            "messages": messages,
            "created_at": conv.created_at.isoformat() if conv.created_at else None
        })

    # 5. Reviews
    reviews_written = []
    for r in db.query(Review).filter(Review.reviewer_id == user.id).all():
        reviews_written.append({
            "listing_id": r.listing_id,
            "reviewee_name": r.reviewee.full_name if r.reviewee else "Deleted User",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
        
    reviews_received = []
    for r in db.query(Review).filter(Review.reviewee_id == user.id).all():
        reviews_received.append({
            "listing_id": r.listing_id,
            "reviewer_name": r.reviewer.full_name if r.reviewer else "Deleted User",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    # 6. Notifications
    notifications = []
    for n in db.query(Notification).filter(Notification.user_id == user.id).all():
        notifications.append({
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        })

    return {
        "profile": profile,
        "listings": listings,
        "saved_listings": saved_listings,
        "conversations": conversations,
        "reviews_written": reviews_written,
        "reviews_received": reviews_received,
        "notifications": notifications
    }


@router.delete("/delete")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get user listing IDs for orphan cleanup
    user_listings = db.query(Listing).filter(Listing.user_id == user.id).all()
    user_listing_ids = [l.id for l in user_listings]

    # 1. Delete notifications
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)

    # 2. Delete saved listings (cascade deletes them too, but explicitly is safer)
    db.query(SavedListing).filter(SavedListing.user_id == user.id).delete(synchronize_session=False)
    if user_listing_ids:
        # Delete SavedListing records where user's listings are saved by others (orphan cleanup)
        db.query(SavedListing).filter(SavedListing.listing_id.in_(user_listing_ids)).delete(synchronize_session=False)
        # Delete views of user's listings
        db.query(ListingView).filter(ListingView.listing_id.in_(user_listing_ids)).delete(synchronize_session=False)

    # 3. Delete listing reports
    db.query(ListingReport).filter(ListingReport.reporter_id == user.id).delete(synchronize_session=False)
    if user_listing_ids:
        db.query(ListingReport).filter(ListingReport.listing_id.in_(user_listing_ids)).delete(synchronize_session=False)

    # 4. Handle reviews (delete reviews written by/received by user)
    db.query(Review).filter((Review.reviewer_id == user.id) | (Review.reviewee_id == user.id)).delete(synchronize_session=False)

    # 5. Handle conversations and messages
    user_convs = db.query(Conversation).filter(
        (Conversation.buyer_id == user.id) | (Conversation.seller_id == user.id)
    ).all()
    for conv in user_convs:
        db.query(Message).filter(Message.conversation_id == conv.id).delete(synchronize_session=False)
        db.delete(conv)

    db.query(Message).filter(Message.sender_id == user.id).delete(synchronize_session=False)

    # 6. Delete contact submissions (GDPR: clean up by email address)
    db.query(ContactSubmission).filter(ContactSubmission.email == user.email).delete(synchronize_session=False)

    # 7. Delete listings (cascade delete-orphan handles this, but let's be explicit)
    db.query(Listing).filter(Listing.user_id == user.id).delete(synchronize_session=False)

    # 8. Delete user
    db.delete(user)
    db.commit()

    return {"detail": "Account deleted successfully. All personal data removed."}
