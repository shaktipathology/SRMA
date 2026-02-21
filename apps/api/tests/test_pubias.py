"""Tests for POST /api/v1/pubias/assess (Phase 9 — publication bias assessment)."""
from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ── Fake data ─────────────────────────────────────────────────────────────────

FAKE_FUNNEL_RESULT = {
    "egger_pval": 0.42,
    "trimfill_effect": 0.68,
    "trimfill_ci_lower": 0.50,
    "trimfill_ci_upper": 0.88,
    "funnel_plot": base64.b64encode(b"fake-funnel-png").decode(),
}

VALID_REQUEST = {
    "study_labels": ["Smith 2020", "Jones 2021", "Lee 2022"],
    "effect_sizes": [0.65, 0.78, 0.72],
    "standard_errors": [0.10, 0.12, 0.09],
    "measure": "RR",
    "method": "REML",
}


@pytest.fixture
def mock_funnel():
    with patch(
        "app.services.stats_worker.run_funnel",
        new_callable=AsyncMock,
        return_value=FAKE_FUNNEL_RESULT,
    ) as m:
        yield m


# ── Happy-path tests ──────────────────────────────────────────────────────────


async def test_pubias_returns_201(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.status_code == 201


async def test_pubias_returns_egger_pval(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.status_code == 201
    assert r.json()["egger_pval"] == pytest.approx(0.42)


async def test_pubias_returns_trimfill(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    body = r.json()
    assert body["trimfill_effect"] == pytest.approx(0.68)
    assert body["trimfill_ci_lower"] == pytest.approx(0.50)
    assert body["trimfill_ci_upper"] == pytest.approx(0.88)


async def test_pubias_returns_valid_funnel_plot(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    png_bytes = base64.b64decode(r.json()["funnel_plot"])
    assert len(png_bytes) > 0


async def test_pubias_assessment_low_concern(client: AsyncClient, mock_funnel):
    """egger_pval >= 0.10 → low_concern."""
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["assessment"] == "low_concern"


async def test_pubias_assessment_possible_concern(client: AsyncClient):
    """egger_pval in [0.05, 0.10) → possible_concern."""
    result = {**FAKE_FUNNEL_RESULT, "egger_pval": 0.07}
    with patch("app.services.stats_worker.run_funnel",
               new_callable=AsyncMock, return_value=result):
        r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["assessment"] == "possible_concern"


async def test_pubias_assessment_high_concern(client: AsyncClient):
    """egger_pval < 0.05 → high_concern."""
    result = {**FAKE_FUNNEL_RESULT, "egger_pval": 0.02}
    with patch("app.services.stats_worker.run_funnel",
               new_callable=AsyncMock, return_value=result):
        r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["assessment"] == "high_concern"


async def test_pubias_phase_is_9(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["phase"] == 9


async def test_pubias_status_complete(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["status"] == "complete"


async def test_pubias_n_studies(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.json()["n_studies"] == 3


async def test_pubias_with_review_id(client: AsyncClient, mock_funnel, db_session):
    """review_id is stored in the response when a real review is provided."""
    from app.models.review import Review

    review = Review(title="PubBias Review", status="draft")
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    r = await client.post("/api/v1/pubias/assess",
                          json={**VALID_REQUEST, "review_id": str(review.id)})
    assert r.status_code == 201
    assert r.json()["review_id"] == str(review.id)


async def test_pubias_persists_phase_result(client: AsyncClient, mock_funnel,
                                             db_session):
    """A PhaseResult row with phase_number=9 should be written to DB."""
    from sqlalchemy import select
    from app.models.phase_result import PhaseResult
    from app.models.review import Review

    review = Review(title="PubBias Persist Review", status="draft")
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    await client.post("/api/v1/pubias/assess",
                      json={**VALID_REQUEST, "review_id": str(review.id)})

    result = await db_session.execute(
        select(PhaseResult).where(
            PhaseResult.phase_number == 9,
            PhaseResult.review_id == review.id,
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].result_data["egger_pval"] == pytest.approx(0.42)


async def test_pubias_measure_and_method_in_response(client: AsyncClient, mock_funnel):
    r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    body = r.json()
    assert body["measure"] == "RR"
    assert body["method"] == "REML"


# ── Error / validation tests ──────────────────────────────────────────────────


async def test_pubias_502_on_stats_worker_failure(client: AsyncClient):
    """Stats worker error → 502."""
    with patch("app.services.stats_worker.run_funnel",
               new_callable=AsyncMock,
               side_effect=Exception("R crashed")):
        r = await client.post("/api/v1/pubias/assess", json=VALID_REQUEST)
    assert r.status_code == 502


async def test_pubias_422_fewer_than_3_studies(client: AsyncClient):
    """Fewer than 3 studies → 422 (Pydantic validation)."""
    payload = {
        "study_labels": ["A", "B"],
        "effect_sizes": [0.5, 0.6],
        "standard_errors": [0.1, 0.1],
    }
    r = await client.post("/api/v1/pubias/assess", json=payload)
    assert r.status_code == 422


async def test_pubias_422_mismatched_lengths(client: AsyncClient):
    """Mismatched list lengths → 422."""
    payload = {
        "study_labels": ["A", "B", "C"],
        "effect_sizes": [0.5, 0.6],  # only 2
        "standard_errors": [0.1, 0.1, 0.1],
    }
    r = await client.post("/api/v1/pubias/assess", json=payload)
    assert r.status_code == 422
