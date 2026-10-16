import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Float, Integer,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class UserRole(str, enum.Enum):
    customer = "customer"
    provider = "provider"
    admin = "admin"

class JobStatus(str, enum.Enum):
    requested = "Requested"
    accepted = "Accepted"
    in_progress = "In Progress"
    completed = "Completed"
    declined = "Declined"
    cancelled = "Cancelled"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider_profile = relationship(
        "ProviderProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    requests = relationship(
        "ServiceRequest", back_populates="customer", cascade="all, delete-orphan"
    )
    reviews_written = relationship(
        "Review", back_populates="reviewer", cascade="all, delete-orphan"
    )

class ProviderProfile(Base):
    __tablename__ = "provider_profiles"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    service_area = Column(String(255), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)
    user = relationship("User", back_populates="provider_profile")
    categories = relationship("ProviderCategory", back_populates="provider", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="provider", cascade="all, delete-orphan")
    
class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    providers = relationship("ProviderCategory", back_populates="category")
    requests = relationship("ServiceRequest", back_populates="category")

class ProviderCategory(Base):
    __tablename__ = "provider_categories"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("provider_profiles.id"), nullable=False)
    category_id = Column(UUID(as_uuid=False), ForeignKey("categories.id"), nullable=False)
    provider = relationship("ProviderProfile", back_populates="categories")
    category = relationship("Category", back_populates="providers")

class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    customer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=False), ForeignKey("categories.id"), nullable=True)
    description = Column(Text, nullable=False)
    photo_url = Column(String(500), nullable=True)
    location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    customer = relationship("User", back_populates="requests")
    category = relationship("Category", back_populates="requests")
    job = relationship("Job", back_populates="service_request", uselist=False, cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    request_id = Column(UUID(as_uuid=False), ForeignKey("service_requests.id"), unique=True, nullable=False)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("provider_profiles.id"), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.requested, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    service_request = relationship("ServiceRequest", back_populates="job")
    provider = relationship("ProviderProfile", back_populates="jobs")
    review = relationship("Review", back_populates="job", uselist=False, cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id"), unique=True, nullable=False)
    reviewer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    job = relationship("Job", back_populates="review")
    reviewer = relationship("User", back_populates="reviews_written")

class RequestDecline(Base):
    __tablename__ = "request_declines"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    request_id = Column(UUID(as_uuid=False), ForeignKey("service_requests.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("provider_profiles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("request_id", "provider_id"),)
