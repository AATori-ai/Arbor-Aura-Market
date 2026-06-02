import json
import os
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Listing, User
from routes.auth import get_current_user
from schemas import BoostCheckoutRequest

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

BOOST_PRICES = {
    "Bump": {"amount": 199, "name": "Bump - Nosta ylös"},      # €1.99
    "Featured": {"amount": 499, "name": "Featured - Suositeltu"},  # €4.99
}

BOOST_DURATION_DAYS = {
    "Bump": 3,
    "Featured": 7,
}


@router.post("/create-checkout-session")
def create_checkout_session(
    req: BoostCheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.boost_type not in BOOST_PRICES:
        raise HTTPException(status_code=400, detail="Invalid boost type")

    # Verify listing ownership
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to boost this listing")

    if not stripe.api_key:
        # Mock mode: apply boost directly in development
        listing.boost_type = req.boost_type
        listing.is_featured = 1 if req.boost_type == "Featured" else 0
        days = BOOST_DURATION_DAYS.get(req.boost_type, 3)
        listing.boost_expires = datetime.utcnow() + timedelta(days=days)
        db.commit()
        return {"url": "/?payment=success", "id": "cs_mock"}

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {"name": BOOST_PRICES[req.boost_type]["name"]},
                "unit_amount": BOOST_PRICES[req.boost_type]["amount"],
            },
            "quantity": 1,
        }],
        success_url=os.getenv("SITE_URL", "http://localhost:3000") + "/?payment=success",
        cancel_url=os.getenv("SITE_URL", "http://localhost:3000") + "/?payment=cancel",
        metadata={
            "user_id": str(user.id),
            "listing_id": str(req.listing_id),
            "boost_type": req.boost_type,
        },
    )

    return {"url": session.url, "id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not WEBHOOK_SECRET or not stripe.api_key:
        return {"status": "ok", "message": "Stripe not configured"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"].get("user_id", 0))
        listing_id_str = session["metadata"].get("listing_id")
        boost_type = session["metadata"].get("boost_type", "Featured")

        if listing_id_str:
            l = db.query(Listing).filter(Listing.id == int(listing_id_str), Listing.user_id == user_id).first()
        else:
            # Fallback to the old logic if metadata doesn't contain listing_id
            listings = db.query(Listing).filter(
                Listing.user_id == user_id,
                Listing.status == "pending",
                Listing.boost_type == boost_type,
            ).all()
            l = listings[-1] if listings else None

        if l:
            l.boost_type = boost_type
            l.is_featured = 1 if boost_type == "Featured" else 0
            days = BOOST_DURATION_DAYS.get(boost_type, 3)
            l.boost_expires = datetime.utcnow() + timedelta(days=days)
            l.stripe_session_id = session.get("id", "")
            db.commit()

    elif event["type"] == "checkout.session.expired":
        pass  # Could clean up pending unpaid listings

    return {"status": "ok"}

