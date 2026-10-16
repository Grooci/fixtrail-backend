"""Provider profile routes for FixTrail.

Save as app/routers/provider_profile.py and register in app/main.py
(after `app = FastAPI(...)`, next to the other include_router lines):

    from app.routers import provider_profile
    app.include_router(provider_profile.router)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, ProviderCategory, ProviderProfile, User, UserRole

# Use the SAME get_current_user import line that works in provider_jobs.py
from app.routers.auth import get_current_user

router = APIRouter(prefix="/provider", tags=["provider"])


class ProviderProfileUpdate(BaseModel):
    bio: Optional[str] = None
    service_area: Optional[str] = None
    is_available: Optional[bool] = None
    category_ids: Optional[List[str]] = None


def profile_to_dict(profile: ProviderProfile) -> dict:
    return {
        "id": profile.id,
        "bio": profile.bio,
        "service_area": profile.service_area,
        "is_available": profile.is_available,
        "average_rating": profile.average_rating,
        "categories": [
            {"id": pc.category.id, "name": pc.category.name}
            for pc in profile.categories
        ],
    }


def require_provider(user: User) -> None:
    if user.role != UserRole.provider:
        raise HTTPException(status_code=403, detail="Providers only")


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_provider(user)
    profile = (
        db.query(ProviderProfile).filter(ProviderProfile.user_id == user.id).first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No provider profile yet")
    return profile_to_dict(profile)


@router.put("/profile")
def save_profile(
    payload: ProviderProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create the profile if missing, otherwise update it.
    Only the fields you send are changed. If you send category_ids,
    they REPLACE the provider's current categories."""
    require_provider(user)

    profile = (
        db.query(ProviderProfile).filter(ProviderProfile.user_id == user.id).first()
    )
    if not profile:
        profile = ProviderProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.service_area is not None:
        profile.service_area = payload.service_area
    if payload.is_available is not None:
        profile.is_available = payload.is_available

    if payload.category_ids is not None:
        wanted = set(payload.category_ids)
        found = (
            db.query(Category).filter(Category.id.in_(wanted)).all() if wanted else []
        )
        if len(found) != len(wanted):
            raise HTTPException(
                status_code=400, detail="One or more categories were not found"
            )
        profile.categories.clear()
        db.flush()
        for category in found:
            profile.categories.append(ProviderCategory(category_id=category.id))

    db.commit()
    db.refresh(profile)
    return profile_to_dict(profile)
