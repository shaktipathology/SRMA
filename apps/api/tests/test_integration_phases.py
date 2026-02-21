"""
Full 11-phase pipeline integration test.

Exercises every phase endpoint end-to-end using a single shared review_id.
External services are mocked; DB writes are real (test DB).
"""
from __future__ import annotations

import base64

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.review import Review
from tests.conftest import FAKE_GRADE_OUTCOME, FAKE_PICO, FAKE_SOF_REQUEST

pytestmark = pytest.mark.asyncio(loop_scope="session")

Q = "Does statin therapy reduce all-cause mortality in adults with heart failure?"


async def _create_papers(db: AsyncSession, review_id, n: int) -> list[Paper]:
    papers = []
    for i in range(n):
        p = Paper(
            review_id=review_id,
            title=f"Integration test paper {i+1}",
            abstract=f"Abstract for integration test paper {i+1}.",
            status="pending",
        )
        db.add(p)
        papers.append(p)
    await db.commit()
    for p in papers:
        await db.refresh(p)
    return papers


@pytest_asyncio.fixture(scope="session")
async def integration_review(db_session: AsyncSession) -> Review:
    """Dedicated review for the full 11-phase pipeline test."""
    review = Review(
        title="Integration Test: Statin therapy in heart failure",
        description="Full pipeline integration test fixture",
        status="draft",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


async def test_full_11_phase_pipeline(
    client: AsyncClient,
    db_session: AsyncSession,
    integration_review: Review,
    mock_claude_pico,
    mock_claude_search,
    mock_minio,
    mock_ncbi,
):
    rid = str(integration_review.id)

    # ------------------------------------------------------------------
    # Phase 1 — Protocol / PICO extraction
    # ------------------------------------------------------------------
    r1 = await client.post(
        "/api/v1/protocol",
        json={"review_id": rid, "research_question": Q},
    )
    assert r1.status_code == 201, f"Phase 1 failed: {r1.text}"
    assert r1.json()["pico_schema"] is not None

    # ------------------------------------------------------------------
    # Phase 2 — Search query construction
    # ------------------------------------------------------------------
    r2 = await client.post(
        "/api/v1/search/build",
        json={"review_id": rid, "pico_schema": FAKE_PICO},
    )
    assert r2.status_code == 201, f"Phase 2 failed: {r2.text}"
    assert r2.json()["search_string"]

    # ------------------------------------------------------------------
    # Phase 3/4 — Title/abstract screening
    # ------------------------------------------------------------------
    papers = await _create_papers(db_session, integration_review.id, 3)
    paper_ids = [str(p.id) for p in papers]

    from unittest.mock import AsyncMock, patch

    # Mock screen_paper to return include for both agents
    fake_agent_result = (
        {"label": "include", "reasoning": "Relevant study"},
        {"label": "include", "reasoning": "Relevant study"},
    )

    with patch(
        "app.services.screener.screen_paper",
        new_callable=AsyncMock,
        return_value=fake_agent_result,
    ):
        r3 = await client.post(
            "/api/v1/screen/batch",
            json={"paper_ids": paper_ids, "review_id": rid},
        )
    assert r3.status_code == 201, f"Phase 3/4 screening failed: {r3.text}"

    # ------------------------------------------------------------------
    # Phase 5 — Full-text screening (real endpoint, screener mocked)
    # ------------------------------------------------------------------
    fake_ft_agents = (
        {"label": "include", "reasoning": "Full text confirms eligibility."},
        {"label": "include", "reasoning": "Design meets criteria."},
    )
    with patch(
        "app.services.screener.screen_fulltext_paper",
        new_callable=AsyncMock,
        return_value=fake_ft_agents,
    ):
        r5 = await client.post(
            "/api/v1/fulltext/screen",
            json={"review_id": rid},
        )
    assert r5.status_code == 201, f"Phase 5 fulltext screening failed: {r5.text}"
    assert r5.json()["screened"] > 0

    # ------------------------------------------------------------------
    # Phase 6 — Data extraction (real endpoint, Claude mocked)
    # ------------------------------------------------------------------
    fake_extracted = {
        "study_design": "randomised controlled trial",
        "population": "Adults with HF",
        "n_total": 500, "n_intervention": 250, "n_control": 250,
        "mean_age": 65.0, "percent_female": 42.0,
        "setting": "multicentre", "country": "USA",
        "intervention": "Statin", "comparator": "Placebo",
        "follow_up_months": 12.0,
        "outcomes": [{"name": "Mortality", "measure_type": "RR", "value": 0.72,
                      "ci_lower": 0.55, "ci_upper": 0.92, "p_value": 0.008,
                      "time_point": "12 months"}],
        "notes": None,
    }
    with patch(
        "app.services.claude.extract_paper_data",
        new_callable=AsyncMock,
        return_value=fake_extracted,
    ):
        r6 = await client.post(
            "/api/v1/extract",
            json={"review_id": rid},
        )
    assert r6.status_code == 201, f"Phase 6 extract failed: {r6.text}"
    assert r6.json()["extracted"] > 0

    # ------------------------------------------------------------------
    # Phases 7, 9 — Stub endpoints
    # ------------------------------------------------------------------
    stub_cases = [
        (7, "/api/v1/rob/assess", {"overall_rob": "low"}),
        (9, "/api/v1/pubias/assess", {"egger_pval": 0.32}),
    ]

    for expected_phase, path, payload in stub_cases:
        r = await client.post(path, json={"review_id": rid, "payload": payload})
        assert r.status_code == 201, f"Phase {expected_phase} stub failed: {r.text}"
        body = r.json()
        assert body["phase"] == expected_phase, (
            f"Expected phase={expected_phase}, got {body['phase']}"
        )

    # ------------------------------------------------------------------
    # Phase 8 — Real meta-analysis (stats worker mocked)
    # ------------------------------------------------------------------
    import base64 as _b64
    fake_pool = {
        "pooled_effect": 0.72, "ci_lower": 0.55, "ci_upper": 0.92,
        "i2": 25.0, "tau2": 0.01, "q_pval": 0.34,
        "pred_lower": 0.40, "pred_upper": 1.10,
        "forest_plot": _b64.b64encode(b"fake-png").decode(),
    }
    with patch(
        "app.services.stats_worker.run_pool",
        new_callable=AsyncMock,
        return_value=fake_pool,
    ):
        r8 = await client.post(
            "/api/v1/meta",
            json={
                "review_id": rid,
                "study_labels": ["A", "B", "C"],
                "effect_sizes": [0.65, 0.78, 0.72],
                "standard_errors": [0.10, 0.12, 0.09],
                "measure": "RR",
            },
        )
    assert r8.status_code == 201, f"Phase 8 meta failed: {r8.text}"
    assert r8.json()["phase"] == 8
    assert r8.json()["status"] == "complete"

    # ------------------------------------------------------------------
    # Phase 10 — GRADE certainty assessment (pure rule-based, no Claude)
    # ------------------------------------------------------------------
    r10 = await client.post(
        "/api/v1/grade",
        json={"review_id": rid, "outcomes": [FAKE_GRADE_OUTCOME]},
    )
    assert r10.status_code == 201, f"Phase 10 GRADE failed: {r10.text}"
    grade_out = r10.json()["outcomes"][0]
    assert grade_out["certainty"] in ("high", "moderate", "low", "very_low")
    assert grade_out["grade_symbol"] in ("⊕⊕⊕⊕", "⊕⊕⊕⊝", "⊕⊕⊝⊝", "⊕⊝⊝⊝")
    # FAKE_GRADE_OUTCOME is an RCT with all domains clean → should be high
    assert grade_out["certainty"] == "high"

    # ------------------------------------------------------------------
    # Phase 11a — SoF table
    # ------------------------------------------------------------------
    r11a = await client.post("/api/v1/sof", json=FAKE_SOF_REQUEST)
    assert r11a.status_code == 201, f"Phase 11a SoF failed: {r11a.text}"
    docx_bytes = base64.b64decode(r11a.json()["docx_b64"])
    assert docx_bytes[:4] == b"PK\x03\x04"  # valid DOCX (ZIP) magic

    # ------------------------------------------------------------------
    # Phase 11b — Full manuscript assembly (no Claude narratives)
    # ------------------------------------------------------------------
    r11b = await client.post(
        "/api/v1/manuscript",
        json={"review_id": rid, "use_claude_narratives": False},
    )
    assert r11b.status_code == 201, f"Phase 11b manuscript failed: {r11b.text}"
    ms_body = r11b.json()
    assert ms_body["word_count"] > 0
    assert len(ms_body["sections_included"]) > 0
    docx_bytes = base64.b64decode(ms_body["docx_b64"])
    assert docx_bytes[:4] == b"PK\x03\x04"

    # ------------------------------------------------------------------
    # Phase 11c — PRISMA 2020 validation
    # ------------------------------------------------------------------
    r11c = await client.post("/api/v1/prisma/validate", json={"review_id": rid})
    assert r11c.status_code == 200, f"Phase 11c PRISMA failed: {r11c.text}"
    prisma_body = r11c.json()
    assert prisma_body["total_items"] == 27
    assert len(prisma_body["checklist"]) == 27

    # After phases 1+2: items 5 (PICO/eligibility) and 7 (search) must be satisfied
    satisfied_items = {
        i["item_number"]
        for i in prisma_body["checklist"]
        if i["status"] == "satisfied"
    }
    assert 5 in satisfied_items, "Item 5 (eligibility/PICO) should be satisfied"
    assert 7 in satisfied_items, "Item 7 (search strategy) should be satisfied"

    # Counts must be consistent
    total = (
        prisma_body["satisfied"]
        + prisma_body["partial"]
        + prisma_body["missing"]
        + prisma_body["not_applicable"]
    )
    assert total == 27
