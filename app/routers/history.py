from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, JobStatus, ProviderProfile, ServiceRequest, User, UserRole
from app.schemas import (
    CustomerHistoryOut, ProviderHistoryItem, ProviderHistoryOut, RequestSummary,
)
from app.routers.auth import get_current_user  # same import as before

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/customer", response_model=CustomerHistoryOut)
def customer_history(
    status: Optional[JobStatus] = None,
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.customer:
        raise HTTPException(403, "Customers only")

    q = (
        db.query(ServiceRequest)
        .outerjoin(Job, Job.request_id == ServiceRequest.id)
        .filter(ServiceRequest.customer_id == user.id)
    )

    if status == JobStatus.requested:
        # a request with no job yet is still "Requested"
        q = q.filter((Job.id.is_(None)) | (Job.status == JobStatus.requested))
    elif status:
        q = q.filter(Job.status == status)

    total = q.count()
    order = ServiceRequest.created_at.desc() if sort == "newest" else ServiceRequest.created_at.asc()
    rows = q.order_by(order).offset(offset).limit(limit).all()

    items = []
    for r in rows:
        job = r.job
        items.append(
            RequestSummary(
                request_id=r.id,
                description=r.description,
                category_name=r.category.name if r.category else None,
                status=job.status.value if job else JobStatus.requested.value,
                provider_name=job.provider.user.full_name if job else None,
                job_id=job.id if job else None,
                has_review=bool(job and job.review),
                created_at=r.created_at,
            )
        )
    return CustomerHistoryOut(total=total, items=items)


@router.get("/provider", response_model=ProviderHistoryOut)
def provider_history(
    status: Optional[JobStatus] = None,
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.provider:
        raise HTTPException(403, "Providers only")

    profile = db.query(ProviderProfile).filter(ProviderProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "Create your provider profile first")

    q = db.query(Job).filter(Job.provider_id == profile.id)
    if status:
        q = q.filter(Job.status == status)

    total = q.count()
    order = Job.updated_at.desc() if sort == "newest" else Job.updated_at.asc()
    jobs = q.order_by(order).offset(offset).limit(limit).all()

    items = [
        ProviderHistoryItem(
            job_id=j.id,
            request_id=j.request_id,
            description=j.service_request.description,
            category_name=j.service_request.category.name if j.service_request.category else None,
            customer_name=j.service_request.customer.full_name,
            status=j.status.value,
            rating=j.review.rating if j.review else None,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in jobs
    ]
    return ProviderHistoryOut(total=total, items=items)