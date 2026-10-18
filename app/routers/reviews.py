from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, JobStatus, ProviderProfile, Review, User, UserRole
from app.schemas import ProviderReviewsOut, ReviewCreate, ReviewOut
from app.routers.auth import get_current_user  # adjust to wherever yours lives

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _to_out(review: Review, reviewer_name: str) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        job_id=review.job_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.customer:
        raise HTTPException(403, "Only customers can leave reviews")

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.service_request.customer_id != user.id:
        raise HTTPException(403, "You can only review your own jobs")
    if job.status != JobStatus.completed:
        raise HTTPException(400, "You can only review completed jobs")
    if job.review is not None:
        raise HTTPException(409, "This job has already been reviewed")

    review = Review(
        job_id=job.id,
        reviewer_id=user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.flush()  # so the new review is included in the average below

    avg = (
        db.query(func.avg(Review.rating))
        .join(Job, Review.job_id == Job.id)
        .filter(Job.provider_id == job.provider_id)
        .scalar()
    )
    job.provider.average_rating = round(float(avg), 2) if avg else 0.0

    db.commit()
    db.refresh(review)
    return _to_out(review, user.full_name)


@router.get("/provider/{provider_id}", response_model=ProviderReviewsOut)
def provider_reviews(provider_id: str, db: Session = Depends(get_db)):
    provider = db.query(ProviderProfile).filter(ProviderProfile.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    rows = (
        db.query(Review, User.full_name)
        .join(Job, Review.job_id == Job.id)
        .join(User, Review.reviewer_id == User.id)
        .filter(Job.provider_id == provider_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return ProviderReviewsOut(
        average_rating=provider.average_rating,
        total_reviews=len(rows),
        reviews=[_to_out(r, name) for r, name in rows],
    )