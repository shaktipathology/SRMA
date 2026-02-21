"""
Stub endpoints for Phases 5–9.

Each endpoint accepts a generic payload, persists a PhaseResult row,
and returns a StubResponse with phase number and ID.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.phase_result import PhaseResult
from app.schemas.stubs import StubRequest, StubResponse

router = APIRouter()

PHASE_NAMES: dict = {}  # all phases now have real implementations
