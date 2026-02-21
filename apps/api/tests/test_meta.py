"""Tests for POST /api/v1/meta (Phase 8 — real meta-analysis via stats worker)."""
from __future__ import annotations

import base64
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.review import Review

pytestmark = pytest.mark.asyncio(loop_scope="session")

FAKE_POOL_RESULT = {
    "pooled_effect": 0.72,
    "ci_lower": 0.55,
    "ci_upper": 0.92,
    "i2": 22.5,
    "tau2": 0.01,
    "q_pval": 0.34,
    "pred_lower": 0.40,
    "pred_upper": 1.10,
    "forest_plot": base64.b64encode(b"fake-png-bytes").decode(),
}

VALID_REQUEST = {
    "study_labels": ["Smith 2020", "Jones 2021", "Lee 2022"],
    "effect_sizes": [0.65, 0.78, 0.72],
    "standard_errors": [0.10, 0.12, 0.09],
    "measure": "RR",
    "method": "REML",
}


@pytest.fixture
def mock_stats_worker():
    with patch(
        "app.services.stats_worker.run_pool",
        new_callable=AsyncMock,
        return_value=FAKE_POOL_RESULT,
    ) as m:
        yield m


async def test_meta_returns_201(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    assert r.status_code == 201


async def test_meta_returns_pooled_stats(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    assert r.status_code == 201
    body = r.json()
    assert body["pooled_effect"] == pytest.approx(0.72)
    assert body["ci_lower"] == pytest.approx(0.55)
    assert body["ci_upper"] == pytest.approx(0.92)
    assert body["i2"] == pytest.approx(22.5)
    assert body["tau2"] == pytest.approx(0.01)
    assert body["q_pval"] == pytest.approx(0.34)


async def test_meta_returns_prediction_interval(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    body = r.json()
    assert body["pred_lower"] == pytest.approx(0.40)
    assert body["pred_upper"] == pytest.approx(1.10)


async def test_meta_returns_forest_plot_base64(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    body = r.json()
    assert "forest_plot" in body
    assert len(body["forest_plot"]) > 0
    # Must be valid base64
    base64.b64decode(body["forest_plot"])


async def test_meta_status_complete(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    body = r.json()
    assert body["status"] == "complete"
    assert body["phase"] == 8


async def test_meta_echoes_inputs(client: AsyncClient, mock_stats_worker):
    r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    body = r.json()
    assert body["measure"] == "RR"
    assert body["method"] == "REML"
    assert body["n_studies"] == 3


async def test_meta_persists_with_review_id(
    client: AsyncClient, mock_stats_worker, real_review: Review
):
    req = {**VALID_REQUEST, "review_id": str(real_review.id)}
    r = await client.post("/api/v1/meta", json=req)
    assert r.status_code == 201
    body = r.json()
    assert body["review_id"] == str(real_review.id)
    assert "id" in body


async def test_meta_stats_worker_called_with_correct_payload(
    client: AsyncClient, mock_stats_worker
):
    await client.post("/api/v1/meta", json=VALID_REQUEST)
    mock_stats_worker.assert_called_once()
    call_payload = mock_stats_worker.call_args[0][0]
    assert call_payload["study_labels"] == VALID_REQUEST["study_labels"]
    assert call_payload["effect_sizes"] == VALID_REQUEST["effect_sizes"]
    assert call_payload["measure"] == "RR"


async def test_meta_stats_worker_502_on_failure(client: AsyncClient):
    with patch(
        "app.services.stats_worker.run_pool",
        new_callable=AsyncMock,
        side_effect=Exception("R crashed"),
    ):
        r = await client.post("/api/v1/meta", json=VALID_REQUEST)
    assert r.status_code == 502
    assert "Stats worker error" in r.json()["detail"]


async def test_meta_rejects_single_study(client: AsyncClient, mock_stats_worker):
    req = {
        "study_labels": ["Only study"],
        "effect_sizes": [0.5],
        "standard_errors": [0.1],
        "measure": "MD",
        "method": "REML",
    }
    r = await client.post("/api/v1/meta", json=req)
    assert r.status_code == 422


async def test_meta_rejects_mismatched_lengths(client: AsyncClient, mock_stats_worker):
    req = {
        "study_labels": ["A", "B"],
        "effect_sizes": [0.5],
        "standard_errors": [0.1, 0.2],
        "measure": "MD",
        "method": "REML",
    }
    r = await client.post("/api/v1/meta", json=req)
    assert r.status_code == 422


async def test_meta_stub_removed_from_stubs_router(client: AsyncClient, mock_stats_worker):
    """Confirm the old stub route /api/v1/meta/run no longer returns stub status."""
    # The real endpoint is now at /api/v1/meta (POST)
    # /api/v1/meta/run should 404 since we replaced it
    r = await client.post("/api/v1/meta/run", json={"review_id": None, "payload": {}})
    assert r.status_code == 404
