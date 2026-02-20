"""Tests for POST /api/v1/search/build (Phase 2)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.review import Review
from tests.conftest import FAKE_PICO, FAKE_SEARCH_RESULT

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_build_search_basic(
    client: AsyncClient, mock_claude_search, mock_ncbi
):
    """Search build returns search string, yield, and rationale."""
    response = await client.post(
        "/api/v1/search/build",
        json={"pico_schema": FAKE_PICO},
    )
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["search_string"] == FAKE_SEARCH_RESULT["search_string"]
    assert data["estimated_yield"] == 1234
    assert data["database"] == "pubmed"
    assert data["claude_model"] == "claude-sonnet-4-6"
    assert data["rationale"] == FAKE_SEARCH_RESULT["rationale"]
    assert "id" in data


async def test_build_search_with_ids(
    client: AsyncClient, mock_claude_search, mock_ncbi, real_review: Review
):
    """review_id are stored and returned."""
    response = await client.post(
        "/api/v1/search/build",
        json={
            "review_id": str(real_review.id),
            "pico_schema": FAKE_PICO,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["review_id"] == str(real_review.id)


async def test_build_search_claude_called(
    client: AsyncClient, mock_claude_search, mock_ncbi
):
    """Claude build_pubmed_search is called with the provided pico_schema."""
    await client.post(
        "/api/v1/search/build",
        json={"pico_schema": FAKE_PICO},
    )
    mock_claude_search.assert_called_once_with(FAKE_PICO)


async def test_build_search_ncbi_called(
    client: AsyncClient, mock_claude_search, mock_ncbi
):
    """NCBI get_pubmed_count is called with the Claude-generated search string."""
    await client.post(
        "/api/v1/search/build",
        json={"pico_schema": FAKE_PICO},
    )
    mock_ncbi.assert_called_once_with(FAKE_SEARCH_RESULT["search_string"])


async def test_build_search_claude_error(client: AsyncClient, mock_ncbi):
    """If Claude raises, the endpoint returns 502."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.claude.build_pubmed_search",
        new_callable=AsyncMock,
        side_effect=Exception("Rate limit"),
    ):
        response = await client.post(
            "/api/v1/search/build",
            json={"pico_schema": FAKE_PICO},
        )
    assert response.status_code == 502
    assert "Claude API error" in response.json()["detail"]


async def test_build_search_ncbi_failure_is_nonfatal(
    client: AsyncClient, mock_claude_search
):
    """If NCBI raises, estimated_yield is None but the request succeeds."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.ncbi.get_pubmed_count",
        new_callable=AsyncMock,
        side_effect=Exception("NCBI timeout"),
    ):
        response = await client.post(
            "/api/v1/search/build",
            json={"pico_schema": FAKE_PICO},
        )
    assert response.status_code == 201, response.text
    assert response.json()["estimated_yield"] is None
