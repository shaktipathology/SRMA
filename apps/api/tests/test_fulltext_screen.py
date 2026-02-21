"""Tests for POST /api/v1/fulltext/screen (Phase 5 — full-text eligibility screening)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.review import Review

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ── Helpers ───────────────────────────────────────────────────────────────────

_FAKE_AGENTS = (
    {"label": "include", "reasoning": "Full text confirms eligibility."},
    {"label": "include", "reasoning": "Design and population meet criteria."},
)


@pytest.fixture
def mock_ft_screener():
    with patch(
        "app.services.screener.screen_fulltext_paper",
        new_callable=AsyncMock,
        return_value=_FAKE_AGENTS,
    ) as m:
        yield m


async def _make_review(db: AsyncSession, label: str = "include") -> tuple[Review, list[Paper]]:
    """Create a review with two papers already at title/abstract-include label."""
    review = Review(
        title=f"FT Test Review {uuid.uuid4().hex[:6]}",
        status="draft",
    )
    db.add(review)
    await db.flush()

    papers = []
    for i in range(2):
        p = Paper(
            review_id=review.id,
            title=f"FT Paper {i + 1}",
            abstract=f"Abstract for FT paper {i + 1}.",
            screening_label=label,
            status="pending",
        )
        db.add(p)
        papers.append(p)

    await db.commit()
    await db.refresh(review)
    for p in papers:
        await db.refresh(p)
    return review, papers


# ── Happy-path tests ──────────────────────────────────────────────────────────


async def test_fulltext_screen_by_paper_ids(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """Explicit paper_ids → screens exactly those papers."""
    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={
            "review_id": str(review.id),
            "paper_ids": [str(p.id) for p in papers],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["screened"] == 2
    assert body["duplicates_removed"] == 0


async def test_fulltext_screen_auto_select_by_review_id(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """No paper_ids → auto-selects include/uncertain papers for the review."""
    review, papers = await _make_review(db_session, label="include")
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 201
    assert r.json()["screened"] == 2


async def test_fulltext_screen_uncertain_papers_included(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """Papers with screening_label='uncertain' should also be auto-selected."""
    review, papers = await _make_review(db_session, label="uncertain")
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 201
    assert r.json()["screened"] == 2


async def test_fulltext_screen_response_has_decisions(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """Response should include a decision for each screened paper."""
    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body["decisions"]) == 2
    for d in body["decisions"]:
        assert d["agent1_label"] == "include"
        assert d["agent2_label"] == "include"
        assert d["final_label"] == "include"
        assert d["stage"] == "fulltext"


async def test_fulltext_screen_cohen_kappa_present(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """cohen_kappa is returned as a float or None (None when single-class agreement)."""
    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    kappa = r.json()["cohen_kappa"]
    # kappa is None when all labels are the same class (undefined); otherwise float
    assert kappa is None or isinstance(kappa, float)


async def test_fulltext_screen_updates_paper_label(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """After screening, the paper's screening_label should reflect the final decision."""
    review, papers = await _make_review(db_session)
    await client.post(
        "/api/v1/fulltext/screen",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    await db_session.refresh(papers[0])
    assert papers[0].screening_label == "include"


async def test_fulltext_screen_exclude_outcome(
    client: AsyncClient, db_session: AsyncSession
):
    """When agents agree on exclude, final_label is exclude."""
    fake_exclude = (
        {"label": "exclude", "reasoning": "Wrong population."},
        {"label": "exclude", "reasoning": "Wrong study design."},
    )
    review, papers = await _make_review(db_session)
    with patch(
        "app.services.screener.screen_fulltext_paper",
        new_callable=AsyncMock,
        return_value=fake_exclude,
    ):
        r = await client.post(
            "/api/v1/fulltext/screen",
            json={"paper_ids": [str(p.id) for p in papers]},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["excluded"] == 2
    for d in body["decisions"]:
        assert d["final_label"] == "exclude"


async def test_fulltext_screen_uncertain_when_agents_disagree(
    client: AsyncClient, db_session: AsyncSession
):
    """When agents disagree (include vs exclude), final_label should be uncertain."""
    fake_disagree = (
        {"label": "include", "reasoning": "Looks relevant."},
        {"label": "exclude", "reasoning": "Wrong design."},
    )
    review, papers = await _make_review(db_session, label="include")
    # Use just 1 paper to make assertion simple
    with patch(
        "app.services.screener.screen_fulltext_paper",
        new_callable=AsyncMock,
        return_value=fake_disagree,
    ):
        r = await client.post(
            "/api/v1/fulltext/screen",
            json={"paper_ids": [str(papers[0].id)]},
        )
    assert r.status_code == 201
    assert r.json()["decisions"][0]["final_label"] == "uncertain"


async def test_fulltext_screen_stage_is_fulltext(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """ScreeningDecision rows must be persisted with stage='fulltext'."""
    from sqlalchemy import select
    from app.models.screening_decision import ScreeningDecision

    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201

    result = await db_session.execute(
        select(ScreeningDecision).where(
            ScreeningDecision.paper_id.in_([p.id for p in papers]),
            ScreeningDecision.stage == "fulltext",
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 2


async def test_fulltext_screen_agent_error_falls_back_to_uncertain(
    client: AsyncClient, db_session: AsyncSession
):
    """If screen_fulltext_paper raises, paper should be classified as uncertain."""
    review, papers = await _make_review(db_session)
    with patch(
        "app.services.screener.screen_fulltext_paper",
        new_callable=AsyncMock,
        side_effect=Exception("Claude unavailable"),
    ):
        r = await client.post(
            "/api/v1/fulltext/screen",
            json={"paper_ids": [str(p.id) for p in papers]},
        )
    assert r.status_code == 201
    for d in r.json()["decisions"]:
        assert d["final_label"] == "uncertain"


async def test_fulltext_screen_with_inclusion_criteria(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """Passing inclusion_criteria should succeed and be forwarded to the screener."""
    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={
            "paper_ids": [str(p.id) for p in papers],
            "inclusion_criteria": "RCTs only; adults ≥18; HF diagnosis confirmed",
        },
    )
    assert r.status_code == 201
    # Verify screener was called with the criteria
    call_kwargs = mock_ft_screener.call_args_list[0].kwargs
    assert "criteria" in call_kwargs
    assert "RCTs only" in call_kwargs["criteria"]


# ── Error-path tests ──────────────────────────────────────────────────────────


async def test_fulltext_screen_422_when_no_ids_or_review(client: AsyncClient):
    """Request with no review_id and no paper_ids should return 422."""
    r = await client.post("/api/v1/fulltext/screen", json={})
    assert r.status_code == 422


async def test_fulltext_screen_404_when_no_eligible_papers(
    client: AsyncClient, db_session: AsyncSession
):
    """If all papers for a review are already excluded, return 404."""
    review, _ = await _make_review(db_session, label="exclude")
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 404


async def test_fulltext_screen_counts_consistent(
    client: AsyncClient, db_session: AsyncSession, mock_ft_screener
):
    """included + excluded + uncertain == screened."""
    review, papers = await _make_review(db_session)
    r = await client.post(
        "/api/v1/fulltext/screen",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    total = body["included"] + body["excluded"] + body["uncertain"]
    assert total == body["screened"]
