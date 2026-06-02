from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from email_service import email_listing_approved, email_listing_rejected
from models import ContactSubmission, Listing, User
from routes.auth import get_admin_user
from schemas import AdminStats, ContactResponse, ListingResponse, UserResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/listings", response_model=list[ListingResponse])
def admin_listings(
    status: str = Query("pending"),
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(Listing).order_by(Listing.created_at.desc())
    if status and status != "all":
        q = q.filter(Listing.status == status)
    result = []
    for l in q.all():
        owner = db.query(User).filter(User.id == l.user_id).first()
        l_r = ListingResponse.model_validate(l)
        if owner:
            l_r.seller_name = owner.full_name or owner.email.split("@")[0]
            l_r.seller_email = owner.email
        result.append(l_r)
    return result


@router.put("/listings/{listing_id}/approve", response_model=ListingResponse)
def approve_listing(listing_id: int, user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    l.status = "approved"
    db.commit()
    db.refresh(l)
    owner = db.query(User).filter(User.id == l.user_id).first()
    l_r = ListingResponse.model_validate(l)
    if owner:
        l_r.seller_name = owner.full_name or owner.email.split("@")[0]
        l_r.seller_email = owner.email
        # Send email notification
        email_listing_approved(owner.email, l.title_fi or l.title_en, l.id)
    return l_r


@router.put("/listings/{listing_id}/reject", response_model=ListingResponse)
def reject_listing(listing_id: int, user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    l.status = "rejected"
    db.commit()
    db.refresh(l)
    owner = db.query(User).filter(User.id == l.user_id).first()
    l_r = ListingResponse.model_validate(l)
    if owner:
        l_r.seller_name = owner.full_name or owner.email.split("@")[0]
        l_r.seller_email = owner.email
        # Send rejection email
        reason = "Listing did not meet our guidelines."
        email_listing_rejected(owner.email, l.title_fi or l.title_en, reason)
    return l_r


@router.delete("/listings/{listing_id}")
def admin_delete_listing(listing_id: int, user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    l = db.query(Listing).filter(Listing.id == listing_id).first()
    if not l:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(l)
    db.commit()
    return {"status": "ok", "message": "Listing deleted by admin"}


@router.get("/users", response_model=list[UserResponse])
def admin_list_users(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: int, user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin users")
    db.delete(target)
    db.commit()
    return {"status": "ok", "message": "User deleted (GDPR compliance)"}


@router.get("/stats", response_model=AdminStats)
def admin_stats(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    total_listings = db.query(Listing).count()
    pending = db.query(Listing).filter(Listing.status == "pending").count()
    approved = db.query(Listing).filter(Listing.status == "approved").count()
    total_users = db.query(User).count()
    total_contacts = db.query(ContactSubmission).count()
    # Boost revenue: Bump=1.99, Featured=4.99 (in euros)
    bump_count = db.query(Listing).filter(Listing.boost_type == "Bump").count()
    feat_count = db.query(Listing).filter(Listing.boost_type == "Featured").count()
    revenue = bump_count * 1.99 + feat_count * 4.99
    return AdminStats(
        total_listings=total_listings,
        pending_listings=pending,
        approved_listings=approved,
        total_users=total_users,
        total_contacts=total_contacts,
        boost_revenue_eur=round(revenue, 2),
    )


@router.get("/contacts", response_model=list[ContactResponse])
def admin_list_contacts(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(ContactSubmission).order_by(ContactSubmission.created_at.desc()).all()


@router.put("/contacts/{contact_id}/read")
def admin_mark_contact_read(contact_id: int, user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    c = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    c.is_read = 1
    db.commit()
    return {"status": "ok", "message": "Marked as read"}
