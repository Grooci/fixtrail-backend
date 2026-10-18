from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, ProviderCategory, ProviderProfile, Review, User
from app.schemas import ProviderPublicOut
from app.routers.auth import get_current_user  # same import as before

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderPublicOut])
def list_providers(
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        db.query(ProviderProfile)
        .join(User, ProviderProfile.user_id == User.id)
        .filter(User.is_active.is_(True))
    )
    if category_id:
        q = q.join(ProviderCategory, ProviderCategory.provider_id == ProviderProfile.id).filter(
            ProviderCategory.category_id == category_id
        )

    profiles = q.order_by(ProviderProfile.average_rating.desc()).all()

    counts = dict(
        db.query(Job.provider_id, func.count(Review.id))
        .join(Review, Review.job_id == Job.id)
        .group_by(Job.provider_id)
        .all()
    )

    return [
        ProviderPublicOut(
            id=p.id,
            name=p.user.full_name,
            bio=p.bio,
            service_area=p.service_area,
            is_available=p.is_available,
            average_rating=p.average_rating,
            total_reviews=counts.get(p.id, 0),
            categories=[pc.category.name for pc in p.categories],
        )
        for p in profiles
    ]