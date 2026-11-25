from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HouseholdProfile
from app.db.session import get_db
from app.schemas.profile import HouseholdProfileCreate, HouseholdProfileOut

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=HouseholdProfileOut, status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    payload: HouseholdProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> HouseholdProfileOut:
    """Create a household profile, or update an existing profile if matching id is provided."""
    profile_id = payload.id or uuid4().hex[:12]
    existing = await db.scalar(select(HouseholdProfile).where(HouseholdProfile.id == profile_id))

    if existing is not None:
        for field, value in payload.model_dump(exclude={"id"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return HouseholdProfileOut.model_validate(existing)

    profile = HouseholdProfile(id=profile_id, **payload.model_dump(exclude={"id"}))
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return HouseholdProfileOut.model_validate(profile)


@router.get("/{profile_id}", response_model=HouseholdProfileOut)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> HouseholdProfileOut:
    """Retrieve a household profile by ID."""
    profile = await db.scalar(select(HouseholdProfile).where(HouseholdProfile.id == profile_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile '{profile_id}' not found.")
    return HouseholdProfileOut.model_validate(profile)
