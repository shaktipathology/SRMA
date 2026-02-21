"""Tests for POST /api/v1/manuscript (manuscript assembler)."""
from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_manuscript_returns_201(client: AsyncClient, real_review: Review):
    r = await client.post(
        "/api/v1/manuscript",
        json={"review_id": str(real_review.id), "use_claude_narratives": False},
    )
    assert r.status_code == 201


async def test_manuscript_valid_docx(client: AsyncClient, real_review: Review):
    r = await client.post(
        "/api/v1/manuscript",
        json={"review_id": str(real_review.id), "use_claude_narratives": False},
    )
    assert r.status_code == 201
    docx_bytes = base64.b64decode(r.json()["docx_b64"])
    # DOCX ZIP magic bytes
    assert docx_bytes[:4] == b"PK\x03\x04"


async def test_manuscript_word_count_positive(client: AsyncClient, real_review: Review):
    r = await client.post(
        "/api/v1/manuscript",
        json={"review_id": str(real_review.id), "use_claude_narratives": False},
    )
    assert r.status_code == 201
    assert r.json()["word_count"] > 0


async def test_manuscript_sections_included_non_empty(client: AsyncClient, real_review: Review):
    r = await client.post(
        "/api/v1/manuscript",
        json={"review_id": str(real_review.id), "use_claude_narratives": False},
    )
    assert r.status_code == 201
    assert len(r.json()["sections_included"]) > 0


async def test_manuscript_missing_phase_data_for_fresh_review(
    client: AsyncClient, db_session: AsyncSession
):
    """A review with no phase data should report several missing sections."""
    fresh = Review(title="Fresh review no data", status="draft")
    db_session.add(fresh)
    await db_session.commit()
    await db_session.refresh(fresh)

    r = await client.post(
        "/api/v1/manuscript",
        json={"review_id": str(fresh.id), "use_claude_narratives": False},
    )
    assert r.status_code == 201
    missing = r.json()["missing_phase_data"]
    assert len(missing) > 0


async def test_manuscript_with_custom_title(client: AsyncClient, real_review: Review):
    r = await client.post(
        "/api/v1/manuscript",
        json={
            "review_id": str(real_review.id),
            "title": "Custom Title for My SR",
            "use_claude_narratives": False,
        },
    )
    assert r.status_code == 201
    assert r.json()["word_count"] > 0
