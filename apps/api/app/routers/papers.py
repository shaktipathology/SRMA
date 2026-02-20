from fastapi import APIRouter, HTTPException
from typing import List, Optional

router = APIRouter()


@router.get("")
async def list_papers(skip: int = 0, limit: int = 20, query: Optional[str] = None):
    # TODO: implement database query
    return {"papers": [], "total": 0, "skip": skip, "limit": limit}


@router.get("/{paper_id}")
async def get_paper(paper_id: str):
    # TODO: fetch from database
    raise HTTPException(status_code=404, detail="Paper not found")


@router.post("")
async def upload_paper():
    # TODO: handle PDF upload and Grobid processing
    return {"message": "Upload endpoint placeholder"}
