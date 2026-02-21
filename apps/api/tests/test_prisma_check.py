"""Tests for POST /api/v1/prisma/validate (PRISMA 2020 checklist validator)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review
from tests.conftest import FAKE_GRADE_OUTCOME, FAKE_PICO, FAKE_SEARCH_RESULT

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _prisma_for(client: AsyncClient, review_id: str):
    r = await client.post("/api/v1/prisma/validate", json={"review_id": review_id})
    assert r.status_code == 200
    return r.json()


async def test_prisma_returns_27_items(client: AsyncClient, real_review: Review):
    data = await _prisma_for(client, str(real_review.id))
    assert data["total_items"] == 27
    assert len(data["checklist"]) == 27


async def test_prisma_item_numbers_sequential(client: AsyncClient, real_review: Review):
    data = await _prisma_for(client, str(real_review.id))
    numbers = [item["item_number"] for item in data["checklist"]]
    assert numbers == list(range(1, 28))


async def test_prisma_fresh_review_many_missing(client: AsyncClient, db_session: AsyncSession):
    """A brand-new review with no data should have several missing items."""
    fresh = Review(title="PRISMA test fresh review", status="draft")
    db_session.add(fresh)
    await db_session.commit()
    await db_session.refresh(fresh)

    data = await _prisma_for(client, str(fresh.id))
    assert data["missing"] > 0
    assert data["is_compliant"] is False


async def test_prisma_title_satisfied(client: AsyncClient, db_session: AsyncSession):
    """A review with a non-empty title satisfies item 1."""
    rev = Review(title="My great review", status="draft")
    db_session.add(rev)
    await db_session.commit()
    await db_session.refresh(rev)

    data = await _prisma_for(client, str(rev.id))
    item1 = next(i for i in data["checklist"] if i["item_number"] == 1)
    assert item1["status"] == "satisfied"


async def test_prisma_items_5_7_satisfied_after_phases_1_2(
    client: AsyncClient,
    real_review: Review,
    mock_claude_pico,
    mock_claude_search,
    mock_minio,
    mock_ncbi,
):
    """After running phase 1 (protocol) and phase 2 (search), items 5 and 7 should be satisfied."""
    rid = str(real_review.id)

    # Phase 1
    await client.post(
        "/api/v1/protocol",
        json={"review_id": rid, "research_question": "PRISMA test question"},
    )
    # Phase 2
    await client.post(
        "/api/v1/search/build",
        json={"review_id": rid, "pico_schema": FAKE_PICO},
    )

    data = await _prisma_for(client, rid)
    checklist = {i["item_number"]: i for i in data["checklist"]}
    assert checklist[5]["status"] == "satisfied", "Item 5 (eligibility) should be satisfied"
    assert checklist[7]["status"] == "satisfied", "Item 7 (search strategy) should be satisfied"
    assert checklist[6]["status"] == "satisfied", "Item 6 (info sources) should be satisfied"


async def test_prisma_items_16_21_missing_without_phases_8_9(
    client: AsyncClient, db_session: AsyncSession
):
    """Without phases 8/9 data, items 16–21 should be missing."""
    rev = Review(title="Missing phases review", status="draft")
    db_session.add(rev)
    await db_session.commit()
    await db_session.refresh(rev)

    data = await _prisma_for(client, str(rev.id))
    checklist = {i["item_number"]: i for i in data["checklist"]}

    for item_num in [16, 17, 18, 19, 20, 21]:
        assert checklist[item_num]["status"] in ("missing", "partial"), \
            f"Item {item_num} should be missing or partial without phases 8/9"


async def test_prisma_item_22_missing_without_grade(
    client: AsyncClient, db_session: AsyncSession
):
    """Without GRADE data (phase 10), item 22 should be missing."""
    rev = Review(title="No GRADE review", status="draft")
    db_session.add(rev)
    await db_session.commit()
    await db_session.refresh(rev)

    data = await _prisma_for(client, str(rev.id))
    checklist = {i["item_number"]: i for i in data["checklist"]}
    assert checklist[22]["status"] == "missing"


async def test_prisma_not_compliant_when_missing_gt_0(
    client: AsyncClient, db_session: AsyncSession
):
    rev = Review(title="Non-compliant review", status="draft")
    db_session.add(rev)
    await db_session.commit()
    await db_session.refresh(rev)

    data = await _prisma_for(client, str(rev.id))
    if data["missing"] > 0:
        assert data["is_compliant"] is False
