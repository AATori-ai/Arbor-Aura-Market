from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# --- Auth ---
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str
    role: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Categories ---
class CategoryResponse(BaseModel):
    id: int
    slug: str
    name_fi: str
    name_en: str
    emoji: str

    model_config = {"from_attributes": True}


# --- Municipalities ---
class MunicipalityResponse(BaseModel):
    id: int
    name_fi: str
    name_en: str

    model_config = {"from_attributes": True}


# --- Listings ---
class ListingCreate(BaseModel):
    title_fi: str
    title_en: str
    category_id: int
    condition: str
    price: float
    location: str
    description: str = ""
    images: str = "[]"
    boost_type: str = "Free"


class ListingUpdate(BaseModel):
    title_fi: Optional[str] = None
    title_en: Optional[str] = None
    category_id: Optional[int] = None
    condition: Optional[str] = None
    price: Optional[float] = None
    location: Optional[str] = None
    description: Optional[str] = None
    images: Optional[str] = None
    boost_type: Optional[str] = None


class ListingResponse(BaseModel):
    id: int
    user_id: int
    category_id: int
    title_fi: str
    title_en: str
    description: str
    condition: str
    price: float
    location: str
    images: str
    boost_type: str
    boost_expires: Optional[datetime] = None
    status: str
    is_featured: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    seller_name: str = ""
    seller_email: str = ""

    model_config = {"from_attributes": True}


# --- Favorites ---
class SavedListingResponse(BaseModel):
    id: int
    user_id: int
    listing_id: int
    created_at: Optional[datetime] = None
    listing: Optional[ListingResponse] = None

    model_config = {"from_attributes": True}


# --- Contact ---
class ContactCreate(BaseModel):
    name: str
    email: str
    subject: str = ""
    message: str


class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    is_read: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Admin Stats ---
class AdminStats(BaseModel):
    total_listings: int
    pending_listings: int
    approved_listings: int
    total_users: int
    total_contacts: int
    boost_revenue_eur: float


# --- Profile & Boost Requests ---
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class BoostCheckoutRequest(BaseModel):
    listing_id: int
    boost_type: str

