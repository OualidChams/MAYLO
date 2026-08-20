"""
Simplified restaurant CRUD — enough for now to register a test restaurant
and link it to a Twilio number, to verify the Days 1-2 Definition of Done.

Protected by a stopgap shared-secret (see app/core/security.py) — NOT the
real authorization model. All requests need an `X-Admin-Key` header.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_key
from app.db.models import Organization, Restaurant
from app.db.session import get_db

router = APIRouter(prefix="/restaurants", tags=["restaurants"], dependencies=[Depends(require_admin_key)])


class RestaurantCreate(BaseModel):
    name: str
    phone_number: str  # E.164, e.g. +14155551234 — must match the Twilio number exactly
    timezone: str = "UTC"
    language: str = "en"
    # Optional for now: no real onboarding/auth flow exists yet (Phase 12).
    # If omitted, a matching Organization is auto-created so the Phase 1
    # test flow (README curl example) keeps working unchanged. Real
    # onboarding will always pass an existing organization_id.
    organization_id: uuid.UUID | None = None


class RestaurantOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    phone_number: str
    timezone: str
    language: str
    active: bool

    class Config:
        from_attributes = True


@router.post("", response_model=RestaurantOut)
async def create_restaurant(payload: RestaurantCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Restaurant).where(Restaurant.phone_number == payload.phone_number))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="A restaurant with this phone_number already exists")

    organization_id = payload.organization_id
    if organization_id is None:
        organization = Organization(name=payload.name)
        db.add(organization)
        await db.flush()  # assigns organization.id without a separate commit
        organization_id = organization.id

    restaurant = Restaurant(**payload.model_dump(exclude={"organization_id"}), organization_id=organization_id)
    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)
    return restaurant


@router.get("/{restaurant_id}", response_model=RestaurantOut)
async def get_restaurant(restaurant_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Restaurant).where(Restaurant.id == restaurant_id))
    restaurant = result.scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.get("", response_model=list[RestaurantOut])
async def list_restaurants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Restaurant))
    return list(result.scalars().all())
