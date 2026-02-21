"""Tests for the GRADE engine (service) and POST /api/v1/grade (router)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.grade_engine import assess_outcome, CERTAINTY_SYMBOLS, CERTAINTY_LABELS
from tests.conftest import FAKE_GRADE_OUTCOME

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Unit tests for the grade engine service (pure Python — no DB)
# ---------------------------------------------------------------------------

def _base_outcome(**overrides):
    base = dict(FAKE_GRADE_OUTCOME)
    base.update(overrides)
    return base


def test_rct_starts_high():
    result = assess_outcome(**_base_outcome(study_design="rct"))
    assert result.starting_certainty == "high"


def test_observational_starts_low():
    result = assess_outcome(**_base_outcome(study_design="observational"))
    assert result.starting_certainty == "low"


def test_low_rob_no_downgrade():
    result = assess_outcome(**_base_outcome(rob_summary="low"))
    assert result.rob_decision == 0


def test_some_concerns_rob_downgrade_1():
    result = assess_outcome(**_base_outcome(rob_summary="some_concerns"))
    assert result.rob_decision == 1


def test_high_rob_downgrade_2():
    result = assess_outcome(**_base_outcome(rob_summary="high"))
    assert result.rob_decision == 2


def test_low_i2_no_inconsistency_downgrade():
    result = assess_outcome(**_base_outcome(i2=20.0, prediction_interval_crosses_null=False))
    assert result.inconsistency_decision == 0


def test_moderate_i2_inconsistency_downgrade_1():
    result = assess_outcome(**_base_outcome(i2=55.0, prediction_interval_crosses_null=False))
    assert result.inconsistency_decision == 1


def test_high_i2_inconsistency_downgrade_2():
    result = assess_outcome(**_base_outcome(i2=80.0, prediction_interval_crosses_null=False))
    assert result.inconsistency_decision == 2


def test_pi_crosses_null_with_i2_50_downgrade_2():
    result = assess_outcome(**_base_outcome(i2=55.0, prediction_interval_crosses_null=True))
    assert result.inconsistency_decision == 2


def test_direct_evidence_no_indirectness_downgrade():
    result = assess_outcome(**_base_outcome(directness="direct"))
    assert result.indirectness_decision == 0


def test_minor_concerns_indirectness_downgrade_1():
    result = assess_outcome(**_base_outcome(directness="minor_concerns"))
    assert result.indirectness_decision == 1


def test_major_concerns_indirectness_downgrade_2():
    result = assess_outcome(**_base_outcome(directness="major_concerns"))
    assert result.indirectness_decision == 2


def test_precise_no_imprecision_downgrade():
    # CI does not cross null (RR), large N
    result = assess_outcome(**_base_outcome(
        measure="RR", ci_lower=0.55, ci_upper=0.92, total_n=1200
    ))
    assert result.imprecision_decision == 0


def test_ci_crosses_null_imprecision_downgrade_1():
    result = assess_outcome(**_base_outcome(
        measure="RR", ci_lower=0.7, ci_upper=1.3, total_n=600
    ))
    assert result.imprecision_decision == 1


def test_small_n_and_ci_crosses_null_downgrade_2():
    result = assess_outcome(**_base_outcome(
        measure="RR", ci_lower=0.7, ci_upper=1.3, total_n=150
    ))
    assert result.imprecision_decision == 2


def test_rct_high_certainty_outcome():
    """RCT with all domains clean → high certainty."""
    result = assess_outcome(**_base_outcome(
        study_design="rct", rob_summary="low", i2=10.0,
        prediction_interval_crosses_null=False, directness="direct",
        ci_lower=0.55, ci_upper=0.92, total_n=1200,
        n_studies_for_funnel=5,
    ))
    assert result.certainty == "high"
    assert result.grade_symbol == "⊕⊕⊕⊕"


def test_upgrade_only_for_observational():
    """Upgrade factors must NOT apply to RCTs."""
    result = assess_outcome(**_base_outcome(
        study_design="rct",
        large_effect=True,
        dose_response=True,
    ))
    assert result.upgrade_count == 0
    assert result.upgrade_reasons == []


def test_upgrade_for_observational_large_effect():
    result = assess_outcome(**_base_outcome(
        study_design="observational",
        large_effect=True,
        dose_response=False,
    ))
    assert result.upgrade_count == 1
    assert len(result.upgrade_reasons) >= 1


def test_upgrade_capped_at_1():
    result = assess_outcome(**_base_outcome(
        study_design="observational",
        large_effect=True,
        dose_response=True,
        residual_confounding_direction="towards_null",
    ))
    assert result.upgrade_count == 1


def test_floor_at_very_low():
    """Downgrading from RCT by 3+ should floor at very_low, not below 1."""
    result = assess_outcome(**_base_outcome(
        study_design="rct",
        rob_summary="high",
        i2=80.0,
        prediction_interval_crosses_null=True,
        directness="major_concerns",
        ci_lower=0.5, ci_upper=1.5, total_n=100,
    ))
    assert result.certainty == "very_low"
    assert result.grade_symbol == "⊕⊝⊝⊝"


def test_grade_symbols_match_labels():
    for level, label in CERTAINTY_LABELS.items():
        symbol = CERTAINTY_SYMBOLS[level]
        assert isinstance(symbol, str)
        assert "⊕" in symbol


# ---------------------------------------------------------------------------
# Router tests (HTTP)
# ---------------------------------------------------------------------------

async def test_grade_endpoint_returns_201(client: AsyncClient):
    r = await client.post("/api/v1/grade", json={"outcomes": [FAKE_GRADE_OUTCOME]})
    assert r.status_code == 201


async def test_grade_endpoint_certainty_and_symbol(client: AsyncClient):
    r = await client.post("/api/v1/grade", json={"outcomes": [FAKE_GRADE_OUTCOME]})
    assert r.status_code == 201
    out = r.json()["outcomes"][0]
    assert out["certainty"] in ("high", "moderate", "low", "very_low")
    assert out["grade_symbol"] in ("⊕⊕⊕⊕", "⊕⊕⊕⊝", "⊕⊕⊝⊝", "⊕⊝⊝⊝")


async def test_grade_endpoint_fake_outcome_high(client: AsyncClient):
    """The FAKE_GRADE_OUTCOME (RCT, all domains clean) → high."""
    r = await client.post("/api/v1/grade", json={"outcomes": [FAKE_GRADE_OUTCOME]})
    assert r.status_code == 201
    out = r.json()["outcomes"][0]
    assert out["certainty"] == "high"
    assert out["grade_symbol"] == "⊕⊕⊕⊕"


async def test_grade_multiple_outcomes(client: AsyncClient):
    obs_outcome = dict(FAKE_GRADE_OUTCOME)
    obs_outcome["study_design"] = "observational"
    obs_outcome["outcome_name"] = "Secondary outcome"
    r = await client.post(
        "/api/v1/grade",
        json={"outcomes": [FAKE_GRADE_OUTCOME, obs_outcome]},
    )
    assert r.status_code == 201
    assert len(r.json()["outcomes"]) == 2
