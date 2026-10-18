from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Job, JobStatus, ProviderCategory, ProviderProfile, RequestDecline,
    Review, ServiceRequest, User, UserRole,
)
from app.schemas import (
    CustomerDashboardOut, ProviderDashboardOut, ProviderJobSummary,
    RequestSummary, ReviewOut,
)
from app.routers.auth import get_current_user  # same import as in reviews.py

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/customer", response_model=CustomerDashboardOut)
def customer_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.customer:
        raise HTTPException(403, "Customers only")

    requests = (
        db.query(ServiceRequest)
        .filter(ServiceRequest.customer_id == user.id)
        .order_by(ServiceRequest.created_at.desc())
        .all()
    )

    counts = {s.value: 0 for s in JobStatus}
    summaries = []
    for r in requests:
        job = r.job
        status = job.status.value if job else JobStatus.requested.value
        counts[status] += 1
        summaries.append(
            RequestSummary(
                request_id=r.id,
                description=r.description,
                category_name=r.category.name if r.category else None,
                status=status,
                provider_name=job.provider.user.full_name if job else None,
                job_id=job.id if job else None,
                has_review=bool(job and job.review),
                created_at=r.created_at,
            )
        )

    return CustomerDashboardOut(
        total_requests=len(requests),
        counts=counts,
        recent=summaries[:5],
    )


@router.get("/provider", response_model=ProviderDashboardOut)
def provider_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.provider:
        raise HTTPException(403, "Providers only")

    profile = db.query(ProviderProfile).filter(ProviderProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(404, "Create your provider profile first")

    jobs = db.query(Job).filter(Job.provider_id == profile.id).all()
    active_jobs = [j for j in jobs if j.status in (JobStatus.accepted, JobStatus.in_progress)]
    completed = [j for j in jobs if j.status == JobStatus.completed]

    # Open requests in this provider's categories that nobody has taken
    # and this provider hasn't declined
    category_ids = [pc.category_id for pc in profile.categories]
    declined_ids = [
        d.request_id
        for d in db.query(RequestDecline).filter(RequestDecline.provider_id == profile.id)
    ]
    open_q = (
        db.query(ServiceRequest)
        .outerjoin(Job, Job.request_id == ServiceRequest.id)
        .filter(Job.id.is_(None), ServiceRequest.category_id.in_(category_ids))
    )
    if declined_ids:
        open_q = open_q.filter(ServiceRequest.id.notin_(declined_ids))
    available = open_q.count()

    review_rows = (
        db.query(Review, User.full_name)
        .join(Job, Review.job_id == Job.id)
        .join(User, Review.reviewer_id == User.id)
        .filter(Job.provider_id == profile.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    active = [
        ProviderJobSummary(
            job_id=j.id,
            request_id=j.request_id,
            description=j.service_request.description,
            category_name=j.service_request.category.name if j.service_request.category else None,
            customer_name=j.service_request.customer.full_name,
            location=j.service_request.location,
            status=j.status.value,
            updated_at=j.updated_at,
        )
        for j in sorted(active_jobs, key=lambda j: j.updated_at, reverse=True)
    ]

    return ProviderDashboardOut(
        available_requests=available,
        active_jobs=len(active_jobs),
        completed_jobs=len(completed),
        average_rating=profile.average_rating,
        total_reviews=len(review_rows),
        active=active,
        recent_reviews=[
            ReviewOut(
                id=r.id, job_id=r.job_id, reviewer_id=r.reviewer_id,
                reviewer_name=name, rating=r.rating, comment=r.comment,
                created_at=r.created_at,
            )
            for r, name in review_rows[:5]
        ],
    )