from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Listing, SavedListing, User
from routes.auth import get_current_user
from schemas import ListingResponse, SavedListingResponse

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[SavedListingResponse])
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    saved = db.query(SavedListing).filter(SavedListing.user_id == user.id).order_by(SavedListing.created_at.desc()).all()
    result = []
    for s in saved:
        l = db.query(Listing).filter(Listing.id == s.listing_id).first()
        s_r = SavedListingResponse.model_validate(s)
        if l:
            owner = db.query(User).filter(User.id == l.user_id).first()
            l_r = ListingResponse.model_validate(l)
            if owner:
                l_r.seller_name = owner.full_name or owner.email.split("@")[0]
                l_r.seller_email = owner.email
            s_r.listing = l_r
        result.append(s_r)
    return result


@router.post("/{listing_id}")
def add_favorite(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")

    existing = db.query(SavedListing).filter(
        SavedListing.user_id == user.id,
        SavedListing.listing_id == listing_id,
    ).first()
    if existing:
        return {"status": "ok", "message": "Already saved"}

    s = SavedListing(user_id=user.id, listing_id=listing_id)
    db.add(s)
    db.commit()
    return {"status": "ok", "message": "Listing saved"}


@router.delete("/{listing_id}")
def remove_favorite(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(SavedListing).filter(
        SavedListing.user_id == user.id,
        SavedListing.listing_id == listing_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(s)
    db.commit()
    return {"status": "ok", "message": "Favorite removed"}
