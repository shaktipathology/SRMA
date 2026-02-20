from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.paper import Paper
from app.schemas.paper import PaperList, PaperRead, PaperUpdate

router = APIRouter()


@router.get("", response_model=PaperList)
async def list_papers(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    review_id: uuid.UUID | None = Query(None),
    query: str | None = Query(None),
):
    stmt = select(Paper)
    count_stmt = select(func.count()).select_from(Paper)

    if review_id:
        stmt = stmt.where(Paper.review_id == review_id)
        count_stmt = count_stmt.where(Paper.review_id == review_id)

    if query:
        stmt = stmt.where(Paper.title.ilike(f"%{query}%"))
        count_stmt = count_stmt.where(Paper.title.ilike(f"%{query}%"))

    total = await db.scalar(count_stmt)
    result = await db.execute(
        stmt.order_by(Paper.created_at.desc()).offset(skip).limit(limit)
    )
    papers = result.scalars().all()
    return PaperList(papers=papers, total=total or 0, skip=skip, limit=limit)


@router.get("/{paper_id}", response_model=PaperRead)
async def get_paper(
    paper_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.patch("/{paper_id}", response_model=PaperRead)
async def update_paper(
    paper_id: uuid.UUID,
    body: PaperUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)

    await db.flush()
    await db.refresh(paper)
    return paper


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(
    paper_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await db.delete(paper)
