from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewList, ReviewRead, ReviewUpdate

router = APIRouter()


@router.get("", response_model=ReviewList)
async def list_reviews(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    total = await db.scalar(select(func.count()).select_from(Review))
    result = await db.execute(
        select(Review).order_by(Review.created_at.desc()).offset(skip).limit(limit)
    )
    reviews = result.scalars().all()
    return ReviewList(reviews=reviews, total=total or 0, skip=skip, limit=limit)


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("", response_model=ReviewRead, status_code=201)
async def create_review(
    body: ReviewCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review = Review(title=body.title, description=body.description)
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


@router.patch("/{review_id}", response_model=ReviewRead)
async def update_review(
    review_id: uuid.UUID,
    body: ReviewUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(review, field, value)

    await db.flush()
    await db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review)
