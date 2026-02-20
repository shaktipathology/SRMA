from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()


@router.get("")
async def list_reviews(skip: int = 0, limit: int = 20):
    # TODO: implement database query
    return {"reviews": [], "total": 0, "skip": skip, "limit": limit}


@router.get("/{review_id}")
async def get_review(review_id: str):
    # TODO: fetch from database
    raise HTTPException(status_code=404, detail="Review not found")


@router.post("")
async def create_review():
    # TODO: create a new systematic review project
    return {"message": "Create review endpoint placeholder"}
