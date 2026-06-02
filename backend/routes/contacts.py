from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Category, ContactSubmission, Listing, Municipality, User
from schemas import CategoryResponse, ContactCreate, ContactResponse, MunicipalityResponse

router = APIRouter(prefix="/api", tags=["contacts"])


@router.get("/municipalities", response_model=list[MunicipalityResponse])
def list_municipalities(search: str = Query(""), db: Session = Depends(get_db)):
    q = db.query(Municipality)
    if search:
        q = q.filter(Municipality.name_fi.ilike(f"%{search}%"))
    return q.order_by(Municipality.name_fi).all()


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.id).all()


@router.get("/categories/tree")
def category_tree(db: Session = Depends(get_db)):
    """Return categories as a tree structure (parent → children)."""
    cats = db.query(Category).order_by(Category.id).all()
    result = {}
    for c in cats:
        if c.parent_id is None:
            result[c.id] = {"id": c.id, "slug": c.slug, "name_fi": c.name_fi, "name_en": c.name_en, "emoji": c.emoji, "subcategories": []}
    for c in cats:
        if c.parent_id is not None and c.parent_id in result:
            result[c.parent_id]["subcategories"].append({
                "id": c.id, "slug": c.slug, "name_fi": c.name_fi, "name_en": c.name_en, "emoji": c.emoji,
            })
    return [v for v in result.values()]


@router.post("/contact")
def submit_contact(req: ContactCreate, db: Session = Depends(get_db)):
    sub = ContactSubmission(
        name=req.name,
        email=req.email,
        subject=req.subject,
        message=req.message,
    )
    db.add(sub)
    db.commit()
    return {"status": "ok", "message": "Contact form submitted"}


@router.get("/stats")
def public_stats(db: Session = Depends(get_db)):
    listing_count = db.query(Listing).filter(Listing.status == "approved").count()
    user_count = db.query(User).count()
    return {"listings": listing_count, "users": user_count}
