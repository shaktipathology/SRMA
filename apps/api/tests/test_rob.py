"""Tests for POST /api/v1/rob/assess (Phase 7 — risk of bias assessment)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.review import Review

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ── Fake data ─────────────────────────────────────────────────────────────────

FAKE_ROB2_RESULT = {
    "tool": "rob2",
    "domains": [
        {"name": "Randomization process", "judgment": "low",
         "rationale": "Adequate sequence generation and allocation concealment."},
        {"name": "Deviations from intended interventions", "judgment": "low",
         "rationale": "Double-blind design maintained throughout."},
        {"name": "Missing outcome data", "judgment": "low",
         "rationale": "Loss to follow-up <5% and balanced between arms."},
        {"name": "Measurement of the outcome", "judgment": "low",
         "rationale": "Outcome assessors blinded."},
        {"name": "Selection of the reported result", "judgment": "low",
         "rationale": "Protocol registered; all pre-specified outcomes reported."},
    ],
    "overall_judgment": "low",
    "notes": None,
}

FAKE_ROBINS_RESULT = {
    "tool": "robins-i",
    "domains": [
        {"name": "Confounding", "judgment": "moderate",
         "rationale": "Some residual confounding likely despite adjustment."},
        {"name": "Selection of participants", "judgment": "low",
         "rationale": "Consecutive enrolment."},
        {"name": "Classification of interventions", "judgment": "low",
         "rationale": "Interventions clearly defined."},
        {"name": "Deviations from intended interventions", "judgment": "low",
         "rationale": "No evidence of deviations."},
        {"name": "Missing data", "judgment": "low",
         "rationale": "Complete case analysis, <3% missing."},
        {"name": "Measurement of outcomes", "judgment": "low",
         "rationale": "Outcomes ascertained from medical records."},
        {"name": "Selection of the reported result", "judgment": "moderate",
         "rationale": "Protocol not pre-registered."},
    ],
    "overall_judgment": "moderate",
    "notes": None,
}


@pytest.fixture
def mock_rob_assessor():
    with patch(
        "app.services.claude.assess_rob",
        new_callable=AsyncMock,
        return_value=FAKE_ROB2_RESULT,
    ) as m:
        yield m


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_review_with_papers(
    db: AsyncSession, label: str = "include", n: int = 2
) -> tuple[Review, list[Paper]]:
    review = Review(title=f"RoB Test {uuid.uuid4().hex[:6]}", status="draft")
    db.add(review)
    await db.flush()

    papers = []
    for i in range(n):
        p = Paper(
            review_id=review.id,
            title=f"RoB Paper {i + 1}",
            abstract="Double-blind RCT of statin therapy.",
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


async def test_rob_assess_by_paper_ids(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """Explicit paper_ids → assesses exactly those papers."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["assessed"] == 2
    assert body["successful"] == 2
    assert body["failed"] == 0


async def test_rob_assess_auto_select_by_review_id(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """No paper_ids → auto-selects include-labelled papers."""
    review, papers = await _make_review_with_papers(db_session, label="include")
    r = await client.post(
        "/api/v1/rob/assess",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 201
    assert r.json()["assessed"] == 2


async def test_rob_assess_returns_domains(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """Response assessments should contain domain judgments."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(papers[0].id)]},
    )
    assert r.status_code == 201
    a = r.json()["assessments"][0]
    assert a["tool"] == "rob2"
    assert len(a["domain_judgments"]) == 5
    assert a["overall_judgment"] == "low"
    assert a["status"] == "complete"


async def test_rob_assess_low_risk_count(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """low_risk count should match number of papers with overall_judgment=low."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["low_risk"] == 2
    assert body["some_concerns"] == 0
    assert body["high_risk"] == 0


async def test_rob_assess_some_concerns(
    client: AsyncClient, db_session: AsyncSession
):
    """Papers with some_concerns judgment are counted correctly."""
    fake_some = {**FAKE_ROB2_RESULT, "overall_judgment": "some_concerns"}
    review, papers = await _make_review_with_papers(db_session)
    with patch(
        "app.services.claude.assess_rob",
        new_callable=AsyncMock,
        return_value=fake_some,
    ):
        r = await client.post(
            "/api/v1/rob/assess",
            json={"paper_ids": [str(p.id) for p in papers]},
        )
    assert r.status_code == 201
    assert r.json()["some_concerns"] == 2
    assert r.json()["low_risk"] == 0


async def test_rob_assess_high_risk(
    client: AsyncClient, db_session: AsyncSession
):
    """Papers with high judgment are counted correctly."""
    fake_high = {**FAKE_ROB2_RESULT, "overall_judgment": "high"}
    review, papers = await _make_review_with_papers(db_session)
    with patch(
        "app.services.claude.assess_rob",
        new_callable=AsyncMock,
        return_value=fake_high,
    ):
        r = await client.post(
            "/api/v1/rob/assess",
            json={"paper_ids": [str(papers[0].id)]},
        )
    assert r.status_code == 201
    assert r.json()["high_risk"] == 1


async def test_rob_assess_robins_i_tool(
    client: AsyncClient, db_session: AsyncSession
):
    """ROBINS-I tool returns 7 domains and moderate overall judgment."""
    review, papers = await _make_review_with_papers(db_session)
    with patch(
        "app.services.claude.assess_rob",
        new_callable=AsyncMock,
        return_value=FAKE_ROBINS_RESULT,
    ):
        r = await client.post(
            "/api/v1/rob/assess",
            json={
                "paper_ids": [str(papers[0].id)],
                "tool": "robins-i",
            },
        )
    assert r.status_code == 201
    a = r.json()["assessments"][0]
    assert a["tool"] == "robins-i"
    assert len(a["domain_judgments"]) == 7
    assert a["overall_judgment"] == "moderate"


async def test_rob_assess_tool_forwarded_to_claude(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """The selected tool should be forwarded to claude.assess_rob."""
    review, papers = await _make_review_with_papers(db_session)
    await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(papers[0].id)], "tool": "rob2"},
    )
    call_kwargs = mock_rob_assessor.call_args.kwargs
    assert call_kwargs["tool"] == "rob2"


async def test_rob_assess_persists_to_db(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """RobAssessment rows should be queryable from the DB after assessment."""
    from sqlalchemy import select
    from app.models.rob_assessment import RobAssessment

    review, papers = await _make_review_with_papers(db_session)
    await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    result = await db_session.execute(
        select(RobAssessment).where(
            RobAssessment.paper_id.in_([p.id for p in papers])
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 2
    for row in rows:
        assert row.status == "complete"
        assert row.overall_judgment == "low"


async def test_rob_counts_consistent(
    client: AsyncClient, db_session: AsyncSession, mock_rob_assessor
):
    """low_risk + some_concerns + high_risk + failed == assessed."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/rob/assess",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    total = body["low_risk"] + body["some_concerns"] + body["high_risk"] + body["failed"]
    assert total == body["assessed"]


# ── Error-handling tests ──────────────────────────────────────────────────────


async def test_rob_assess_claude_error_marked_failed(
    client: AsyncClient, db_session: AsyncSession
):
    """When Claude raises, the assessment row should have status='error'."""
    review, papers = await _make_review_with_papers(db_session)
    with patch(
        "app.services.claude.assess_rob",
        new_callable=AsyncMock,
        side_effect=Exception("Claude unavailable"),
    ):
        r = await client.post(
            "/api/v1/rob/assess",
            json={"paper_ids": [str(p.id) for p in papers]},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["failed"] == 2
    assert body["successful"] == 0
    for a in body["assessments"]:
        assert a["status"] == "error"
        assert a["overall_judgment"] is None


async def test_rob_assess_422_no_ids_no_review(client: AsyncClient):
    """No review_id and no paper_ids → 422."""
    r = await client.post("/api/v1/rob/assess", json={})
    assert r.status_code == 422


async def test_rob_assess_404_no_included_papers(
    client: AsyncClient, db_session: AsyncSession
):
    """review_id with no included papers → 404."""
    review, _ = await _make_review_with_papers(db_session, label="exclude")
    r = await client.post(
        "/api/v1/rob/assess",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 404
