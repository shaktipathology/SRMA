"""Tests for POST /api/v1/extract (Phase 6 — structured data extraction)."""
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

FAKE_EXTRACTED = {
    "study_design": "randomised controlled trial",
    "population": "Adults with heart failure",
    "n_total": 500,
    "n_intervention": 250,
    "n_control": 250,
    "mean_age": 65.2,
    "percent_female": 42.5,
    "setting": "multicentre",
    "country": "USA",
    "intervention": "Statin 40 mg/day",
    "comparator": "Placebo",
    "follow_up_months": 12.0,
    "outcomes": [
        {
            "name": "All-cause mortality",
            "measure_type": "RR",
            "value": 0.72,
            "ci_lower": 0.55,
            "ci_upper": 0.92,
            "p_value": 0.008,
            "time_point": "12 months",
        }
    ],
    "notes": None,
}


@pytest.fixture
def mock_extractor():
    with patch(
        "app.services.claude.extract_paper_data",
        new_callable=AsyncMock,
        return_value=FAKE_EXTRACTED,
    ) as m:
        yield m


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_review_with_papers(
    db: AsyncSession, label: str = "include", n: int = 2
) -> tuple[Review, list[Paper]]:
    review = Review(title=f"Extract Test {uuid.uuid4().hex[:6]}", status="draft")
    db.add(review)
    await db.flush()

    papers = []
    for i in range(n):
        p = Paper(
            review_id=review.id,
            title=f"Extract Paper {i + 1}",
            abstract=f"RCT of statin therapy in HF patients. Paper {i + 1}.",
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


async def test_extract_by_paper_ids(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """Explicit paper_ids → extracts exactly those papers."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["extracted"] == 2
    assert body["successful"] == 2
    assert body["failed"] == 0


async def test_extract_auto_select_by_review_id(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """No paper_ids → auto-selects include-labelled papers for the review."""
    review, papers = await _make_review_with_papers(db_session, label="include")
    r = await client.post(
        "/api/v1/extract",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 201
    assert r.json()["extracted"] == 2


async def test_extract_returns_structured_data(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """extracted_data should contain the structured fields from Claude."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(papers[0].id)]},
    )
    assert r.status_code == 201
    ex = r.json()["extractions"][0]
    assert ex["status"] == "complete"
    data = ex["extracted_data"]
    assert data["study_design"] == "randomised controlled trial"
    assert data["n_total"] == 500
    assert len(data["outcomes"]) == 1
    assert data["outcomes"][0]["measure_type"] == "RR"


async def test_extract_status_complete(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """Each extraction row should have status='complete' on success."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    for ex in r.json()["extractions"]:
        assert ex["status"] == "complete"


async def test_extract_paper_id_in_response(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """Each ExtractionOut should include the correct paper_id."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    returned_ids = {ex["paper_id"] for ex in r.json()["extractions"]}
    expected_ids = {str(p.id) for p in papers}
    assert returned_ids == expected_ids


async def test_extract_with_template(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """extraction_template should be forwarded to claude.extract_paper_data."""
    review, papers = await _make_review_with_papers(db_session)
    template = "Focus only on mortality outcomes."
    r = await client.post(
        "/api/v1/extract",
        json={
            "paper_ids": [str(papers[0].id)],
            "extraction_template": template,
        },
    )
    assert r.status_code == 201
    call_kwargs = mock_extractor.call_args.kwargs
    assert call_kwargs["extraction_template"] == template


async def test_extract_persists_to_db(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """DataExtraction rows should be queryable from the DB after extraction."""
    from sqlalchemy import select
    from app.models.data_extraction import DataExtraction

    review, papers = await _make_review_with_papers(db_session)
    await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    result = await db_session.execute(
        select(DataExtraction).where(
            DataExtraction.paper_id.in_([p.id for p in papers])
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 2
    for row in rows:
        assert row.status == "complete"
        assert row.extractor_model is not None


async def test_extract_counts_consistent(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """successful + failed == extracted."""
    review, papers = await _make_review_with_papers(db_session)
    r = await client.post(
        "/api/v1/extract",
        json={"paper_ids": [str(p.id) for p in papers]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["successful"] + body["failed"] == body["extracted"]


# ── Error-handling tests ──────────────────────────────────────────────────────


async def test_extract_claude_error_marked_failed(
    client: AsyncClient, db_session: AsyncSession
):
    """When Claude raises, the extraction row should have status='error'."""
    review, papers = await _make_review_with_papers(db_session)
    with patch(
        "app.services.claude.extract_paper_data",
        new_callable=AsyncMock,
        side_effect=Exception("Claude unavailable"),
    ):
        r = await client.post(
            "/api/v1/extract",
            json={"paper_ids": [str(p.id) for p in papers]},
        )
    assert r.status_code == 201
    body = r.json()
    assert body["failed"] == 2
    assert body["successful"] == 0
    for ex in body["extractions"]:
        assert ex["status"] == "error"


async def test_extract_422_no_ids_no_review(client: AsyncClient):
    """Request with neither review_id nor paper_ids → 422."""
    r = await client.post("/api/v1/extract", json={})
    assert r.status_code == 422


async def test_extract_404_no_included_papers(
    client: AsyncClient, db_session: AsyncSession
):
    """review_id with no included papers → 404."""
    review, _ = await _make_review_with_papers(db_session, label="exclude")
    r = await client.post(
        "/api/v1/extract",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 404


async def test_extract_skips_non_include_labels(
    client: AsyncClient, db_session: AsyncSession, mock_extractor
):
    """Auto-select by review_id should ignore uncertain/excluded papers."""
    review = Review(title=f"Filter Test {uuid.uuid4().hex[:6]}", status="draft")
    db_session.add(review)
    await db_session.flush()

    # One included, one excluded, one uncertain
    labels = ["include", "exclude", "uncertain"]
    for i, lbl in enumerate(labels):
        p = Paper(
            review_id=review.id,
            title=f"Paper {i}",
            abstract="Abstract.",
            screening_label=lbl,
            status="pending",
        )
        db_session.add(p)
    await db_session.commit()

    r = await client.post(
        "/api/v1/extract",
        json={"review_id": str(review.id)},
    )
    assert r.status_code == 201
    # Only the 1 included paper should be extracted
    assert r.json()["extracted"] == 1
