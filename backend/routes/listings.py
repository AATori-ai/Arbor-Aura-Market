from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Category, Listing, User
from routes.auth import get_current_user
from schemas import ListingCreate, ListingResponse, ListingUpdate

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingResponse])
def list_listings(
    response: Response,
    category: str = Query(""),
    location: str = Query(""),
    min_price: float = Query(0),
    max_price: float = Query(0),
    condition: str = Query(""),
    search: str = Query(""),
    sort: str = Query("newest"),
    page: int = Query(1),
    per_page: int = Query(50),
    db: Session = Depends(get_db),
):
    q = db.query(Listing).filter(Listing.status == "approved")

    if category:
        cat_obj = db.query(Category).filter(
            (Category.slug == category) | (Category.name_fi == category) | (Category.name_en == category)
        ).first()
        if cat_obj:
            q = q.filter(Listing.category_id == cat_obj.id)

    if location:
        q = q.filter(Listing.location.ilike(f"%{location}%"))

    if min_price > 0:
        q = q.filter(Listing.price >= min_price)
    if max_price > 0:
        q = q.filter(Listing.price <= max_price)

    if condition:
        q = q.filter(Listing.condition == condition)

    if search:
        s = f"%{search}%"
        q = q.filter(
            (Listing.title_fi.ilike(s)) |
            (Listing.title_en.ilike(s)) |
            (Listing.description.ilike(s)) |
            (Listing.location.ilike(s))
        )

    if sort == "asc":
        q = q.order_by(Listing.price.asc())
    elif sort == "desc":
        q = q.order_by(Listing.price.desc())
    else:
        q = q.order_by(Listing.is_featured.desc(), Listing.created_at.desc())

    total = q.count()
    listings = q.offset((page - 1) * per_page).limit(per_page).all()

    # Add pagination headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Per-Page"] = str(per_page)
    response.headers["X-Total-Pages"] = str((total + per_page - 1) // per_page)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count, X-Page, X-Per-Page, X-Total-Pages"

    # Attach seller info
    result = []
    for l in listings:
        owner = db.query(User).filter(User.id == l.user_id).first()
        l_r = ListingResponse.model_validate(l)
        if owner:
            l_r.seller_name = owner.full_name or owner.email.split("@")[0]
            l_r.seller_email = owner.email
        result.append(l_r)
    return result


@router.get("/my", response_model=list[ListingResponse])
def my_listings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listings = db.query(Listing).filter(Listing.user_id == user.id).order_by(Listing.created_at.desc()).all()
    result = []
    for l in listings:
        l_r = ListingResponse.model_validate(l)
        l_r.seller_name = user.full_name or user.email.split("@")[0]
        l_r.seller_email = user.email
        result.append(l_r)
    return result


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    owner = db.query(User).filter(User.id == l.user_id).first()
    l_r = ListingResponse.model_validate(l)
    if owner:
        l_r.seller_name = owner.full_name or owner.email.split("@")[0]
        l_r.seller_email = owner.email
    return l_r


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(req: ListingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.title_fi.strip() or not req.title_en.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if req.price < 0:
        raise HTTPException(status_code=400, detail="Price must be non-negative")
    cat = db.query(Category).filter(Category.id == req.category_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Invalid category")

    l = Listing(
        user_id=user.id,
        category_id=req.category_id,
        title_fi=req.title_fi,
        title_en=req.title_en,
        description=req.description,
        condition=req.condition,
        price=req.price,
        location=req.location,
        images=req.images or "[]",
        boost_type=req.boost_type,
        status="approved",
    )
    db.add(l)
    db.commit()
    db.refresh(l)

    l_r = ListingResponse.model_validate(l)
    l_r.seller_name = user.full_name or user.email.split("@")[0]
    l_r.seller_email = user.email
    return l_r


@router.put("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id: int, req: ListingUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    if l.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this listing")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(l, key, value)
    l.updated_at = __import__("datetime").datetime.utcnow()
    db.commit()
    db.refresh(l)

    l_r = ListingResponse.model_validate(l)
    l_r.seller_name = user.full_name or user.email.split("@")[0]
    l_r.seller_email = user.email
    return l_r


@router.delete("/{listing_id}")
def delete_listing(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    if l.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this listing")
    db.delete(l)
    db.commit()
    return {"status": "ok", "message": "Listing deleted"}


@router.put("/{listing_id}/sold", response_model=ListingResponse)
def mark_sold(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    if l.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    l.status = "sold"
    db.commit()
    db.refresh(l)
    l_r = ListingResponse.model_validate(l)
    l_r.seller_name = user.full_name or user.email.split("@")[0]
    l_r.seller_email = user.email
    return l_r


@router.put("/{listing_id}/renew", response_model=ListingResponse)
def renew_listing(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    if l.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to renew this listing")
    l.created_at = __import__("datetime").datetime.utcnow()
    l.status = "approved"
    db.commit()
    db.refresh(l)
    l_r = ListingResponse.model_validate(l)
    l_r.seller_name = user.full_name or user.email.split("@")[0]
    l_r.seller_email = user.email
    return l_r
