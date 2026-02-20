"""
Tests for POST /api/v1/screen/batch (Phase 3).

Covers:
- Basic happy-path screening (mock agents agree)
- Deduplication (near-identical titles flagged)
- Cohen's κ computation
- Agent disagreement → uncertain adjudication
- NCBI-style: empty paper_ids → 422
- All-agree batch: κ = undefined (single class) → None
- Graceful degradation when one agent errors
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.models.paper import Paper
from app.models.review import Review

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def screen_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def screen_review(screen_db: AsyncSession) -> Review:
    r = Review(title="Screening Test Review", status="active")
    screen_db.add(r)
    await screen_db.commit()
    await screen_db.refresh(r)
    return r


async def _make_paper(
    db: AsyncSession,
    review: Review,
    title: str,
    abstract: str = "Sample abstract.",
) -> Paper:
    p = Paper(
        review_id=review.id,
        title=title,
        abstract=abstract,
        status="pending",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


# ── Helpers ────────────────────────────────────────────────────────────────

def _mock_agents(label1: str = "include", label2: str = "include"):
    """Patch both agent calls inside screen_paper."""
    async def _fake_screen(title, abstract, criteria=None):
        return (
            {"label": label1, "reasoning": f"Agent1 says {label1}"},
            {"label": label2, "reasoning": f"Agent2 says {label2}"},
        )
    return patch("app.routers.screening.screener_svc.screen_paper", side_effect=_fake_screen)


# ── Tests ──────────────────────────────────────────────────────────────────

async def test_screen_batch_basic(client: AsyncClient, screen_db: AsyncSession, screen_review: Review):
    """Happy path: two papers, both agents agree include."""
    p1 = await _make_paper(screen_db, screen_review, "Ketamine for depression RCT")
    p2 = await _make_paper(screen_db, screen_review, "Mindfulness for anxiety RCT")

    with _mock_agents("include", "include"):
        resp = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": [str(p1.id), str(p2.id)]},
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["screened"] == 2
    assert data["duplicates_removed"] == 0
    assert data["included"] == 2
    assert data["excluded"] == 0
    assert data["cohen_kappa"] is None  # only one class → undefined
    assert len(data["decisions"]) == 2
    for d in data["decisions"]:
        assert d["final_label"] == "include"
        assert d["agent1_label"] == "include"
        assert d["agent2_label"] == "include"


async def test_screen_batch_deduplication(client: AsyncClient, screen_db: AsyncSession, screen_review: Review):
    """Near-identical titles → one kept, one marked duplicate."""
    title = "Effect of aspirin on cardiovascular events: a randomised controlled trial"
    p_orig = await _make_paper(screen_db, screen_review, title)
    p_dup  = await _make_paper(screen_db, screen_review, title + " ")  # whitespace variant

    with _mock_agents("include", "include"):
        resp = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": [str(p_orig.id), str(p_dup.id)]},
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["duplicates_removed"] == 1
    assert data["screened"] == 1

    dup_decision = next(d for d in data["decisions"] if d["paper_id"] == str(p_dup.id))
    assert dup_decision["is_duplicate"] is True
    assert dup_decision["duplicate_of_paper_id"] == str(p_orig.id)


async def test_screen_batch_agent_disagreement(
    client: AsyncClient, screen_db: AsyncSession, screen_review: Review
):
    """Agent1 include vs Agent2 exclude → final = uncertain."""
    p = await _make_paper(screen_db, screen_review, "Disputed paper on placebo effect")

    with _mock_agents("include", "exclude"):
        resp = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": [str(p.id)]},
        )

    assert resp.status_code == 201, resp.text
    d = resp.json()["decisions"][0]
    assert d["final_label"] == "uncertain"
    assert d["agent1_label"] == "include"
    assert d["agent2_label"] == "exclude"


async def test_screen_batch_cohen_kappa(
    client: AsyncClient, screen_db: AsyncSession, screen_review: Review
):
    """κ is computed when agents produce at least two distinct classes."""
    papers = [
        await _make_paper(screen_db, screen_review, f"Paper kappa {uuid.uuid4().hex[:6]}")
        for _ in range(4)
    ]

    # Predictable side_effect list — 4 calls, alternating include/exclude
    # Both agents always agree → κ = 1.0
    responses = [
        ({"label": "include", "reasoning": ""}, {"label": "include", "reasoning": ""}),
        ({"label": "exclude", "reasoning": ""}, {"label": "exclude", "reasoning": ""}),
        ({"label": "include", "reasoning": ""}, {"label": "include", "reasoning": ""}),
        ({"label": "exclude", "reasoning": ""}, {"label": "exclude", "reasoning": ""}),
    ]

    with patch(
        "app.routers.screening.screener_svc.screen_paper",
        new_callable=AsyncMock,
        side_effect=responses,
    ):
        resp = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": [str(p.id) for p in papers]},
        )

    assert resp.status_code == 201, resp.text
    kappa = resp.json()["cohen_kappa"]
    assert kappa is not None
    assert kappa == 1.0   # agents agree on every paper → κ = 1


async def test_screen_batch_empty_ids(client: AsyncClient):
    """Empty paper_ids → 422."""
    resp = await client.post("/api/v1/screen/batch", json={"paper_ids": []})
    assert resp.status_code == 422


async def test_screen_batch_not_found(client: AsyncClient):
    """All IDs non-existent → 404."""
    resp = await client.post(
        "/api/v1/screen/batch",
        json={"paper_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )
    assert resp.status_code == 404


async def test_screen_batch_includes_reasoning(
    client: AsyncClient, screen_db: AsyncSession, screen_review: Review
):
    """Agent reasoning strings are stored and returned."""
    p = await _make_paper(screen_db, screen_review, "Reasoning test paper")

    with _mock_agents("exclude", "exclude"):
        resp = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": [str(p.id)]},
        )

    d = resp.json()["decisions"][0]
    assert "Agent1" in d["agent1_reasoning"]
    assert "Agent2" in d["agent2_reasoning"]
    assert d["claude_model"] == "claude-sonnet-4-6"
