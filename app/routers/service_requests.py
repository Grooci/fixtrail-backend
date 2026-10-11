from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import Category, ServiceRequest, User, UserRole

router = APIRouter(prefix="/requests", tags=["requests"])


class RequestCreate(BaseModel):
    category_id: str
    description: str
    location: str
    photo_url: Optional[str] = None


class RequestOut(BaseModel):
    id: str
    category_id: Optional[str]
    category_name: Optional[str]
    description: str
    photo_url: Optional[str]
    location: Optional[str]
    status: str
    created_at: datetime


def to_out(r: ServiceRequest) -> RequestOut:
    return RequestOut(
        id=r.id,
        category_id=r.category_id,
        category_name=r.category.name if r.category else None,
        description=r.description,
        photo_url=r.photo_url,
        location=r.location,
        # a request has no status until a provider takes it and a job exists
        status=r.job.status.value if r.job else "Requested",
        created_at=r.created_at,
    )


@router.post("", response_model=RequestOut, status_code=201)
def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.customer)),
):
    if not db.query(Category).filter(Category.id == payload.category_id).first():
        raise HTTPException(status_code=400, detail="Category not found")
    if not payload.description.strip():
        raise HTTPException(status_code=400, detail="Description is required")

    req = ServiceRequest(
        customer_id=current_user.id,
        category_id=payload.category_id,
        description=payload.description.strip(),
        location=payload.location.strip(),
        photo_url=payload.photo_url,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return to_out(req)


@router.get("/mine", response_model=List[RequestOut])
def my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(ServiceRequest)
        .filter(ServiceRequest.customer_id == current_user.id)
        .order_by(ServiceRequest.created_at.desc())
        .all()
    )
    return [to_out(r) for r in rows]