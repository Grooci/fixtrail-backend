from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole

class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.customer

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int

class ReviewCreate(BaseModel):
    job_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewOut(BaseModel):
    id: str
    job_id: str
    reviewer_id: str
    reviewer_name: str
    rating: int
    comment: Optional[str]
    created_at: datetime

class ProviderReviewsOut(BaseModel):
    average_rating: float
    total_reviews: int
    reviews: list[ReviewOut]

class RequestSummary(BaseModel):
    request_id: str
    description: str
    category_name: Optional[str]
    status: str
    provider_name: Optional[str]
    job_id: Optional[str]
    has_review: bool
    created_at: datetime

class CustomerDashboardOut(BaseModel):
    total_requests: int
    counts: dict[str, int]
    recent: list[RequestSummary]

class ProviderJobSummary(BaseModel):
    job_id: str
    request_id: str
    description: str
    category_name: Optional[str]
    customer_name: str
    location: Optional[str]
    status: str
    updated_at: datetime

class ProviderDashboardOut(BaseModel):
    available_requests: int
    active_jobs: int
    completed_jobs: int
    average_rating: float
    total_reviews: int
    active: list[ProviderJobSummary]
    recent_reviews: list[ReviewOut]

class CustomerHistoryOut(BaseModel):
    total: int
    items: list[RequestSummary]

class ProviderHistoryItem(BaseModel):
    job_id: str
    request_id: str
    description: str
    category_name: Optional[str]
    customer_name: str
    status: str
    rating: Optional[int]
    created_at: datetime
    updated_at: datetime

class ProviderHistoryOut(BaseModel):
    total: int
    items: list[ProviderHistoryItem]

class ProviderPublicOut(BaseModel):
    id: str
    name: str
    bio: Optional[str]
    service_area: Optional[str]
    is_available: bool
    average_rating: float
    total_reviews: int
    categories: list[str]