from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models import ListingView

router = APIRouter(prefix="/api", tags=["views"])


@router.post("/listings/{listing_id}/view")
def record_view(listing_id: int, request: Request, db: Session = Depends(get_db)):
    viewer_ip = request.client.host if request.client else "unknown"
    view = ListingView(listing_id=listing_id, viewer_ip=viewer_ip)
    db.add(view)
    db.commit()
    return {"status": "ok"}


@router.get("/listings/{listing_id}/views")
def get_view_count(listing_id: int, db: Session = Depends(get_db)):
    count = db.query(ListingView).filter(ListingView.listing_id == listing_id).count()
    return {"listing_id": listing_id, "views": count}
