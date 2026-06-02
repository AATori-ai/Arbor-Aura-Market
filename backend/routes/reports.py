from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from auth import decode_token
from database import get_db
from models import Listing, ListingReport, User
from routes.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])
security = HTTPBearer(auto_error=False)


class ReportCreate(BaseModel):
    listing_id: int
    reason: str
    description: str = ""


class ReportResponse(BaseModel):
    id: int
    listing_id: int
    reporter_id: Optional[int] = None
    reason: str
    description: str
    is_resolved: int
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


def get_optional_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if creds is None:
        return None
    try:
        payload = decode_token(creds.credentials)
        return db.query(User).filter(User.id == int(payload["sub"])).first()
    except Exception:
        return None


@router.post("", status_code=201)
def report_listing(
    req: ReportCreate,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    report = ListingReport(
        listing_id=req.listing_id,
        reporter_id=user.id if user else None,
        reason=req.reason,
        description=req.description,
    )
    db.add(report)
    db.commit()
    return {"status": "ok", "message": "Listing reported. We will review it shortly."}


@router.get("/admin", response_model=list[ReportResponse])
def admin_list_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(ListingReport).order_by(ListingReport.created_at.desc()).all()


@router.put("/admin/{report_id}/resolve")
def admin_resolve_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    report = db.query(ListingReport).filter(ListingReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.is_resolved = 1
    db.commit()
    return {"status": "ok", "message": "Report marked as resolved"}
