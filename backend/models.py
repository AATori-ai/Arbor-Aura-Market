from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, default="")
    phone = Column(String, default="")
    role = Column(String, default="user")  # 'user' | 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listings = relationship("Listing", back_populates="owner", cascade="all, delete-orphan")
    saved = relationship("SavedListing", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String, unique=True, nullable=False)
    name_fi = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    emoji = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    listings = relationship("Listing", back_populates="category", foreign_keys="Listing.category_id")
    children = relationship("Category", backref="parent", remote_side=[id])


class Municipality(Base):
    __tablename__ = "municipalities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_fi = Column(String, nullable=False)
    name_en = Column(String, nullable=False)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    title_fi = Column(String, nullable=False)
    title_en = Column(String, nullable=False)
    description = Column(Text, default="")
    condition = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    images = Column(Text, default="[]")  # JSON string of image paths
    boost_type = Column(String, default="Free")
    boost_expires = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending | approved | rejected | sold
    is_featured = Column(Integer, default=0)
    stripe_session_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="listings")
    category = relationship("Category", back_populates="listings", foreign_keys="Listing.category_id")


class SavedListing(Base):
    __tablename__ = "saved_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_user_listing"),)

    user = relationship("User", back_populates="saved")
    listing = relationship("Listing")


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    subject = Column(String, default="")
    message = Column(Text, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ListingReport(Base):
    __tablename__ = "listing_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String, nullable=False)
    description = Column(Text, default="")
    is_resolved = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing")


class ListingView(Base):
    __tablename__ = "listing_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    viewer_ip = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, default="")
    is_buyer_read = Column(Integer, default=1)
    is_seller_read = Column(Integer, default=1)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", backref="messages")
    sender = relationship("User")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewee = relationship("User", foreign_keys=[reviewee_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # message, review, listing_approved, listing_rejected, listing_expiring
    title = Column(String, nullable=False)
    message = Column(Text, default="")
    related_id = Column(Integer, nullable=True)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
