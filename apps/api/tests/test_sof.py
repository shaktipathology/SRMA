"""Tests for POST /api/v1/sof (SoF table generator)."""
from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient

from tests.conftest import FAKE_SOF_REQUEST

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_sof_returns_201(client: AsyncClient):
    r = await client.post("/api/v1/sof", json=FAKE_SOF_REQUEST)
    assert r.status_code == 201


async def test_sof_returns_valid_base64(client: AsyncClient):
    r = await client.post("/api/v1/sof", json=FAKE_SOF_REQUEST)
    assert r.status_code == 201
    docx_bytes = base64.b64decode(r.json()["docx_b64"])
    # DOCX is a ZIP; first 4 bytes are PK magic
    assert docx_bytes[:4] == b"PK\x03\x04"


async def test_sof_outcomes_count(client: AsyncClient):
    r = await client.post("/api/v1/sof", json=FAKE_SOF_REQUEST)
    assert r.status_code == 201
    assert r.json()["outcomes_count"] == len(FAKE_SOF_REQUEST["outcomes"])


async def test_sof_max_7_outcomes_rejected(client: AsyncClient):
    outcome = FAKE_SOF_REQUEST["outcomes"][0]
    request = {**FAKE_SOF_REQUEST, "outcomes": [outcome] * 8}
    r = await client.post("/api/v1/sof", json=request)
    assert r.status_code == 422


async def test_sof_exactly_7_outcomes_accepted(client: AsyncClient):
    outcome = FAKE_SOF_REQUEST["outcomes"][0]
    outcomes = []
    for i in range(7):
        o = dict(outcome)
        o["outcome_name"] = f"Outcome {i+1}"
        outcomes.append(o)
    request = {**FAKE_SOF_REQUEST, "outcomes": outcomes}
    r = await client.post("/api/v1/sof", json=request)
    assert r.status_code == 201
    assert r.json()["outcomes_count"] == 7


async def test_sof_grade_certainty_values(client: AsyncClient):
    """All GRADE certainty levels generate valid DOCX."""
    for certainty in ("high", "moderate", "low", "very_low"):
        outcome = dict(FAKE_SOF_REQUEST["outcomes"][0])
        outcome["certainty"] = certainty
        request = {**FAKE_SOF_REQUEST, "outcomes": [outcome]}
        r = await client.post("/api/v1/sof", json=request)
        assert r.status_code == 201, f"Failed for certainty={certainty}"
        base64.b64decode(r.json()["docx_b64"])


async def test_sof_with_footnotes(client: AsyncClient):
    outcome = dict(FAKE_SOF_REQUEST["outcomes"][0])
    outcome["footnotes"] = ["RoB concerns", "Indirect population"]
    request = {**FAKE_SOF_REQUEST, "outcomes": [outcome]}
    r = await client.post("/api/v1/sof", json=request)
    assert r.status_code == 201
    base64.b64decode(r.json()["docx_b64"])


async def test_sof_with_optional_title(client: AsyncClient):
    request = {**FAKE_SOF_REQUEST, "title": "Table 2: Summary of Findings"}
    r = await client.post("/api/v1/sof", json=request)
    assert r.status_code == 201
