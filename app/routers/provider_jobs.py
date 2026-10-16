from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Job,
    JobStatus,
    ProviderProfile,
    RequestDecline,
    ServiceRequest,
    User,
    UserRole,
)

# TODO: change this import to wherever your current-user dependency lives.
# It must return the User object from the JWT.
from app.routers.auth import get_current_user

router = APIRouter(prefix="/provider", tags=["provider"])

# The only legal status moves a provider can make on an accepted job.
NEXT_STATUS = {
    JobStatus.accepted: JobStatus.in_progress,
    JobStatus.in_progress: JobStatus.completed,
}


class JobStatusUpdate(BaseModel):
    status: JobStatus


# ---------- helpers ----------

def get_provider_profile(user: User, db: Session) -> ProviderProfile:
    if user.role != UserRole.provider:
        raise HTTPException(status_code=403, detail="Providers only")
    profile = (
        db.query(ProviderProfile).filter(ProviderProfile.user_id == user.id).first()
    )
    if not profile:
        raise HTTPException(
            status_code=400, detail="Create your provider profile first"
        )
    return profile


def request_to_dict(req: ServiceRequest) -> dict:
    return {
        "id": req.id,
        "description": req.description,
        "photo_url": req.photo_url,
        "location": req.location,
        "category_id": req.category_id,
        "category_name": req.category.name if req.category else None,
        "customer_name": req.customer.full_name if req.customer else None,
        "created_at": req.created_at,
    }


def job_to_dict(job: Job) -> dict:
    data = request_to_dict(job.service_request)
    data.update(
        {
            "id": job.id,
            "request_id": job.request_id,
            "status": job.status.value,
            "updated_at": job.updated_at,
        }
    )
    return data


# ---------- browse open requests ----------

@router.get("/requests")
def browse_requests(
    category_id: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Open requests (no job yet) in this provider's categories,
    excluding ones this provider already declined."""
    profile = get_provider_profile(user, db)

    my_category_ids = [pc.category_id for pc in profile.categories]
    declined_ids = [
        row[0]
        for row in db.query(RequestDecline.request_id)
        .filter(RequestDecline.provider_id == profile.id)
        .all()
    ]

    query = (
        db.query(ServiceRequest)
        .options(
            joinedload(ServiceRequest.category),
            joinedload(ServiceRequest.customer),
        )
        .filter(~ServiceRequest.job.has())
        .filter(ServiceRequest.category_id.in_(my_category_ids))
        .filter(~ServiceRequest.id.in_(declined_ids))
    )
    if category_id:
        query = query.filter(ServiceRequest.category_id == category_id)
    if location:
        query = query.filter(ServiceRequest.location.ilike(f"%{location}%"))

    requests = query.order_by(ServiceRequest.created_at.desc()).all()
    return [request_to_dict(r) for r in requests]


# ---------- accept / decline ----------

@router.post("/requests/{request_id}/accept", status_code=201)
def accept_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_provider_profile(user, db)

    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.job:
        raise HTTPException(status_code=409, detail="Request already taken")

    job = Job(
        request_id=req.id,
        provider_id=profile.id,
        status=JobStatus.accepted,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        # jobs.request_id is unique, so if two providers accept at the same
        # moment, the database lets only one through.
        db.rollback()
        raise HTTPException(status_code=409, detail="Request already taken")

    db.refresh(job)
    return job_to_dict(job)


@router.post("/requests/{request_id}/decline")
def decline_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_provider_profile(user, db)

    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.job:
        raise HTTPException(status_code=409, detail="Request already taken")

    already = (
        db.query(RequestDecline)
        .filter(
            RequestDecline.request_id == request_id,
            RequestDecline.provider_id == profile.id,
        )
        .first()
    )
    if not already:
        db.add(RequestDecline(request_id=request_id, provider_id=profile.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {"detail": "Request declined"}


# ---------- my jobs + status tracking ----------

@router.get("/jobs")
def my_jobs(
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_provider_profile(user, db)

    query = (
        db.query(Job)
        .options(
            joinedload(Job.service_request).joinedload(ServiceRequest.category),
            joinedload(Job.service_request).joinedload(ServiceRequest.customer),
        )
        .filter(Job.provider_id == profile.id)
    )
    if status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(Job.updated_at.desc()).all()
    return [job_to_dict(j) for j in jobs]


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    payload: JobStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_provider_profile(user, db)

    job = db.get(Job, job_id)
    if not job or job.provider_id != profile.id:
        raise HTTPException(status_code=404, detail="Job not found")

    expected = NEXT_STATUS.get(job.status)
    if expected is None:
        raise HTTPException(
            status_code=400,
            detail=f"Job is already '{job.status.value}' and cannot be changed",
        )
    if payload.status != expected:
        raise HTTPException(
            status_code=400,
            detail=f"From '{job.status.value}' the only next step is '{expected.value}'",
        )

    job.status = payload.status
    db.commit()
    db.refresh(job)
    return job_to_dict(job)
