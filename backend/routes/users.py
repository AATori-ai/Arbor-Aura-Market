from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import hash_password, validate_password_strength
from database import get_db
from models import Listing, User, Review
from routes.auth import get_current_user
from schemas import ListingResponse, UserResponse, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.put("/me", response_model=UserResponse)
def update_profile(
    req: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.full_name is not None:
        user.full_name = req.full_name
    if req.phone is not None:
        user.phone = req.phone
    if req.password is not None:
        valid, msg = validate_password_strength(req.password)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)
        user.password_hash = hash_password(req.password)

    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/listings", response_model=list[ListingResponse])
def user_public_listings(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    listings = (
        db.query(Listing)
        .filter(Listing.user_id == user_id, Listing.status == "approved")
        .order_by(Listing.created_at.desc())
        .limit(50)
        .all()
    )

    result = []
    for l in listings:
        l_r = ListingResponse.model_validate(l)
        l_r.seller_name = user.full_name or user.email.split("@")[0]
        l_r.seller_email = user.email
        result.append(l_r)
    return result


@router.get("/{user_id}/profile")
def user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    active_count = (
        db.query(Listing).filter(Listing.user_id == user_id, Listing.status == "approved").count()
    )
    sold_count = (
        db.query(Listing).filter(Listing.user_id == user_id, Listing.status == "sold").count()
    )

    # Calculate review stats
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.reviewee_id == user_id).scalar()
    review_count = db.query(Review).filter(Review.reviewee_id == user_id).count()

    return {
        "id": user.id,
        "name": user.full_name or user.email.split("@")[0],
        "email": user.email,
        "phone": user.phone or "",
        "member_since": user.created_at.isoformat() if user.created_at else "",
        "active_listings": active_count,
        "sold_listings": sold_count,
        "average_rating": round(float(avg_rating), 1) if avg_rating else None,
        "review_count": review_count,
    }

