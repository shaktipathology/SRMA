"""Tests for POST /api/v1/protocol (Phase 1)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.review import Review
from tests.conftest import FAKE_PICO

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_protocol_no_review(
    client: AsyncClient, mock_claude_pico, mock_minio
):
    """Protocol can be created without a review_id (standalone)."""
    response = await client.post(
        "/api/v1/protocol",
        json={"research_question": "What is the efficacy of ketamine for treatment-resistant depression?"},
    )
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["version"] == 1
    assert data["research_question"] == "What is the efficacy of ketamine for treatment-resistant depression?"
    assert data["pico_schema"] == FAKE_PICO
    assert data["claude_model"] == "claude-sonnet-4-6"
    assert data["review_id"] is None
    assert "id" in data


async def test_create_protocol_with_review(
    client: AsyncClient, mock_claude_pico, mock_minio, real_review: Review
):
    """Protocol created with a real review_id writes minio_prefix."""
    response = await client.post(
        "/api/v1/protocol",
        json={
            "review_id": str(real_review.id),
            "research_question": "What are the effects of mindfulness on anxiety?",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["review_id"] == str(real_review.id)
    assert data["pico_schema"]["population"] == FAKE_PICO["population"]
    assert data["minio_prefix"] == "reviews/test/protocols/v1"
    mock_minio.assert_called_once()


async def test_create_protocol_claude_called(
    client: AsyncClient, mock_claude_pico, mock_minio
):
    """Claude extract_pico is called exactly once with the research question."""
    question = "Does aspirin reduce cardiovascular events?"
    await client.post("/api/v1/protocol", json={"research_question": question})
    mock_claude_pico.assert_called_once_with(question)


async def test_create_protocol_claude_error(client: AsyncClient, mock_minio):
    """If Claude raises, the endpoint returns 502."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.services.claude.extract_pico",
        new_callable=AsyncMock,
        side_effect=Exception("API timeout"),
    ):
        response = await client.post(
            "/api/v1/protocol",
            json={"research_question": "Does aspirin reduce cardiovascular events?"},
        )
    assert response.status_code == 502
    assert "Claude API error" in response.json()["detail"]


async def test_create_protocol_pico_fields(
    client: AsyncClient, mock_claude_pico, mock_minio
):
    """All PICO fields are returned in the response."""
    response = await client.post(
        "/api/v1/protocol",
        json={"research_question": "PICO field test"},
    )
    assert response.status_code == 201, response.text
    pico = response.json()["pico_schema"]
    assert "population" in pico
    assert "intervention" in pico
    assert "comparator" in pico
    assert isinstance(pico["outcomes"], list)
    assert isinstance(pico["study_designs"], list)
