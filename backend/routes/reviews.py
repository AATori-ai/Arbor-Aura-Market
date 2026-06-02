"""Review routes for ArborAura Market.
Supports creating and viewing reviews for completed transactions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Listing, Review, User, Notification
from routes.auth import get_current_user

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


# ── Schemas ──

class ReviewCreate(BaseModel):
    listing_id: int
    reviewee_id: int
    rating: int  # 1-5
    comment: str = ""


class ReviewResponse(BaseModel):
    id: int
    listing_id: int
    reviewer_id: int
    reviewer_name: str = ""
    reviewee_id: int
    reviewee_name: str = ""
    listing_title: str = ""
    rating: int
    comment: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Routes ──

@router.post("", status_code=201)
def create_review(
    req: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a review for a completed transaction."""
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    if req.reviewee_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot review yourself")

    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Check if user already reviewed this listing
    existing = db.query(Review).filter(
        Review.listing_id == req.listing_id,
        Review.reviewer_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this listing")

    review = Review(
        listing_id=req.listing_id,
        reviewer_id=user.id,
        reviewee_id=req.reviewee_id,
        rating=req.rating,
        comment=req.comment,
    )
    db.add(review)

    # Create notification for the reviewee
    notif = Notification(
        user_id=req.reviewee_id,
        type="review",
        title="Uusi arvostelu / New review",
        message=f"{user.full_name or user.email.split('@')[0]} antoi sinulle {req.rating}⭐ arvostelun",
        related_id=req.listing_id,
    )
    db.add(notif)

    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "listing_id": review.listing_id,
        "rating": review.rating,
        "comment": review.comment,
        "status": "ok",
    }


@router.get("/user/{user_id}")
def get_user_reviews(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Get all reviews received by a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reviews = (
        db.query(Review)
        .filter(Review.reviewee_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    result = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        listing = db.query(Listing).filter(Listing.id == r.listing_id).first()
        result.append({
            "id": r.id,
            "listing_id": r.listing_id,
            "listing_title": (listing.title_fi or listing.title_en) if listing else "",
            "reviewer_id": r.reviewer_id,
            "reviewer_name": (reviewer.full_name or reviewer.email.split("@")[0]) if reviewer else "Deleted User",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    # Compute average rating
    avg = db.query(func.avg(Review.rating)).filter(Review.reviewee_id == user_id).scalar()

    return {
        "reviews": result,
        "count": len(result),
        "average_rating": round(float(avg), 1) if avg else None,
    }


@router.get("/listing/{listing_id}")
def get_listing_reviews(
    listing_id: int,
    db: Session = Depends(get_db),
):
    """Get reviews for a specific listing."""
    reviews = (
        db.query(Review)
        .filter(Review.listing_id == listing_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    result = []
    for r in reviews:
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        result.append({
            "id": r.id,
            "reviewer_id": r.reviewer_id,
            "reviewer_name": (reviewer.full_name or reviewer.email.split("@")[0]) if reviewer else "Deleted User",
            "rating": r.rating,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result
