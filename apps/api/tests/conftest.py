"""
Shared pytest fixtures.

External services (Claude, NCBI, MinIO) are mocked so tests run
without real credentials or network access.

All async fixtures and tests share a single session-scoped event loop
to prevent asyncpg connection pool leaks across test functions.
"""
from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.db import AsyncSessionLocal as async_session_factory
from app.models.review import Review


# ---------------------------------------------------------------------------
# Single shared event loop for the whole test session
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# App client (session-scoped so it shares the same event loop)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# DB session for direct inserts (session-scoped)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# A real Review row so FK tests can reference a valid review_id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def real_review(db_session: AsyncSession) -> Review:
    review = Review(
        title="Test Review for Phase 1 & 2",
        description="Integration test fixture",
        status="draft",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


# ---------------------------------------------------------------------------
# Claude mocks
# ---------------------------------------------------------------------------

FAKE_PICO = {
    "population": "Adults with treatment-resistant depression",
    "intervention": "Ketamine infusion",
    "comparator": "Placebo",
    "outcomes": ["Remission rate", "Response rate", "Adverse events"],
    "study_designs": ["randomised controlled trial", "systematic review"],
}

FAKE_SEARCH_RESULT = {
    "search_string": '(("depression"[MeSH Terms] OR "depression"[Title/Abstract]) AND ("ketamine"[MeSH Terms] OR "ketamine"[Title/Abstract]))',
    "rationale": "Combined MeSH and free-text terms for population and intervention.",
}


@pytest.fixture
def mock_claude_pico():
    with patch(
        "app.services.claude.extract_pico",
        new_callable=AsyncMock,
        return_value=FAKE_PICO,
    ) as m:
        yield m


@pytest.fixture
def mock_claude_search():
    with patch(
        "app.services.claude.build_pubmed_search",
        new_callable=AsyncMock,
        return_value=FAKE_SEARCH_RESULT,
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# MinIO mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_minio():
    with patch(
        "app.services.minio_store.put_protocol_files",
        new_callable=AsyncMock,
        return_value="reviews/test/protocols/v1",
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# NCBI mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ncbi():
    with patch(
        "app.services.ncbi.get_pubmed_count",
        new_callable=AsyncMock,
        return_value=1234,
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# GRADE / manuscript fixtures
# ---------------------------------------------------------------------------

FAKE_GRADE_OUTCOME = {
    "outcome_name": "All-cause mortality",
    "study_design": "rct",
    "n_studies": 5,
    "total_n": 1200,
    "rob_summary": "low",
    "i2": 22.0,
    "prediction_interval_crosses_null": False,
    "directness": "direct",
    "measure": "RR",
    "ci_lower": 0.55,
    "ci_upper": 0.92,
    "effect_size": 0.72,
    "n_studies_for_funnel": 5,
    "large_effect": False,
    "dose_response": False,
    "importance": "critical",
}

FAKE_SOF_REQUEST = {
    "population": "Adults with HF",
    "intervention": "Statin therapy",
    "comparator": "Placebo",
    "outcomes": [
        {
            "outcome_name": "All-cause mortality",
            "importance": "critical",
            "n_studies": 5,
            "n_participants": 1200,
            "effect_measure": "RR",
            "effect_size": 0.72,
            "ci_lower": 0.55,
            "ci_upper": 0.92,
            "certainty": "high",
            "footnotes": [],
        }
    ],
}


@pytest.fixture
def mock_claude_manuscript():
    with patch(
        "app.services.claude.generate_methods_narrative",
        new_callable=AsyncMock,
        return_value="[Methods text]",
    ) as m1, patch(
        "app.services.claude.generate_results_narrative",
        new_callable=AsyncMock,
        return_value="[Results text]",
    ) as m2:
        yield m1, m2
