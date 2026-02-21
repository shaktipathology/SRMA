"""
Pure rule-based GRADE certainty-of-evidence engine.

No external calls. Fully deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


CERTAINTY_LABELS = {4: "high", 3: "moderate", 2: "low", 1: "very_low"}
CERTAINTY_SYMBOLS = {4: "⊕⊕⊕⊕", 3: "⊕⊕⊕⊝", 2: "⊕⊕⊝⊝", 1: "⊕⊝⊝⊝"}
CERTAINTY_START = {"rct": 4, "observational": 2}


@dataclass
class DomainResult:
    decision: int  # 0, 1, or 2 points to downgrade
    rationale: str


@dataclass
class GradeResult:
    starting_certainty: str
    certainty: str
    downgrade_count: int
    upgrade_count: int

    rob_decision: int
    rob_rationale: str
    inconsistency_decision: int
    inconsistency_rationale: str
    indirectness_decision: int
    indirectness_rationale: str
    imprecision_decision: int
    imprecision_rationale: str
    publication_bias_decision: int
    publication_bias_rationale: str

    upgrade_reasons: List[str]
    footnotes: List[str]
    grade_symbol: str


def _assess_rob(rob_summary: str) -> DomainResult:
    if rob_summary == "low":
        return DomainResult(0, "Risk of bias is low across included studies.")
    elif rob_summary == "some_concerns":
        return DomainResult(
            1,
            "Some concerns about risk of bias detected; downgraded 1 level "
            "(at least one domain rated as 'some concerns' in most studies).",
        )
    else:  # high
        return DomainResult(
            2,
            "High risk of bias detected; downgraded 2 levels "
            "(at least one domain rated as 'high risk' in most studies).",
        )


def _assess_inconsistency(
    i2: float, prediction_interval_crosses_null: bool
) -> DomainResult:
    if i2 > 75 or (prediction_interval_crosses_null and i2 >= 50):
        return DomainResult(
            2,
            f"Substantial unexplained heterogeneity (I² = {i2:.0f}%"
            + (", prediction interval crosses null" if prediction_interval_crosses_null else "")
            + "); downgraded 2 levels.",
        )
    elif i2 >= 40:
        return DomainResult(
            1,
            f"Moderate heterogeneity (I² = {i2:.0f}%); downgraded 1 level "
            "(I² threshold ≥ 40%).",
        )
    else:
        return DomainResult(
            0,
            f"Heterogeneity is low (I² = {i2:.0f}%); no downgrade for inconsistency.",
        )


def _assess_indirectness(directness: str) -> DomainResult:
    if directness == "direct":
        return DomainResult(0, "Evidence is direct; population, intervention, and outcomes align with the review question.")
    elif directness == "minor_concerns":
        return DomainResult(
            1,
            "Minor concerns about indirectness (e.g., surrogate outcomes or slightly different population); downgraded 1 level.",
        )
    else:  # major_concerns
        return DomainResult(
            2,
            "Major concerns about indirectness (e.g., different population, intervention, or outcomes); downgraded 2 levels.",
        )


def _assess_imprecision(
    ci_lower: float,
    ci_upper: float,
    measure: str,
    total_n: int,
) -> DomainResult:
    null_val = 1.0 if measure in ("OR", "RR") else 0.0
    crosses_null = ci_lower < null_val < ci_upper

    if total_n < 200 and crosses_null:
        return DomainResult(
            2,
            f"Serious imprecision: 95% CI crosses the null ({ci_lower} to {ci_upper}) "
            f"and total N={total_n} is below the optimal information size threshold of 200; "
            "downgraded 2 levels.",
        )
    elif crosses_null or total_n < 400:
        reasons = []
        if crosses_null:
            reasons.append(f"95% CI crosses the null ({ci_lower} to {ci_upper})")
        if total_n < 400:
            reasons.append(f"total N={total_n} is below OIS threshold of 400")
        return DomainResult(
            1,
            "; ".join(reasons) + "; downgraded 1 level.",
        )
    else:
        return DomainResult(
            0,
            f"Adequate precision: 95% CI ({ci_lower} to {ci_upper}) does not cross the null "
            f"and total N={total_n} exceeds the OIS threshold.",
        )


def _assess_publication_bias(
    n_studies_for_funnel: int,
    egger_pval: Optional[float],
) -> DomainResult:
    if n_studies_for_funnel < 10:
        return DomainResult(
            0,
            f"Publication bias not assessable: fewer than 10 studies (n={n_studies_for_funnel}) "
            "available for funnel plot asymmetry testing.",
        )
    if egger_pval is not None and egger_pval < 0.10:
        return DomainResult(
            1,
            f"Possible publication bias: Egger's test p={egger_pval:.3f} < 0.10; downgraded 1 level.",
        )
    return DomainResult(
        0,
        f"No evidence of publication bias: "
        + (f"Egger's test p={egger_pval:.3f} ≥ 0.10." if egger_pval is not None else "test not performed."),
    )


def _compute_upgrades(
    study_design: str,
    large_effect: bool,
    dose_response: bool,
    residual_confounding_direction: Optional[str],
) -> tuple[int, List[str]]:
    """Upgrading applies only to observational evidence, max net +1."""
    if study_design != "observational":
        return 0, []

    reasons: List[str] = []
    if large_effect:
        reasons.append("Large effect size (OR/RR ≥ 2 or ≤ 0.5): +1 upgrade")
    if dose_response:
        reasons.append("Dose–response gradient present: +1 upgrade")
    if residual_confounding_direction == "towards_null":
        reasons.append("Residual confounding would attenuate the observed effect (towards null): +1 upgrade")

    up = min(1, len(reasons))
    return up, reasons


def assess_outcome(
    outcome_name: str,
    study_design: str,
    n_studies: int,
    total_n: int,
    rob_summary: str,
    i2: float,
    prediction_interval_crosses_null: bool,
    directness: str,
    ci_lower: float,
    ci_upper: float,
    measure: str,
    n_studies_for_funnel: int,
    egger_pval: Optional[float] = None,
    large_effect: bool = False,
    dose_response: bool = False,
    residual_confounding_direction: Optional[str] = None,
    importance: str = "critical",
    **kwargs,  # absorb any extra fields from input schema
) -> GradeResult:
    starting_level = CERTAINTY_START.get(study_design, 4)
    starting_label = CERTAINTY_LABELS[starting_level]

    rob = _assess_rob(rob_summary)
    inconsistency = _assess_inconsistency(i2, prediction_interval_crosses_null)
    indirectness = _assess_indirectness(directness)
    imprecision = _assess_imprecision(ci_lower, ci_upper, measure, total_n)
    pub_bias = _assess_publication_bias(n_studies_for_funnel, egger_pval)

    total_down = min(3, rob.decision + inconsistency.decision + indirectness.decision + imprecision.decision + pub_bias.decision)

    up, upgrade_reasons = _compute_upgrades(
        study_design, large_effect, dose_response, residual_confounding_direction
    )

    final_level = max(1, min(4, starting_level - total_down + up))
    certainty_label = CERTAINTY_LABELS[final_level]
    grade_symbol = CERTAINTY_SYMBOLS[final_level]

    # Build footnotes for domains that downgraded
    footnotes: List[str] = []
    if rob.decision > 0:
        footnotes.append(f"Risk of bias: {rob.rationale}")
    if inconsistency.decision > 0:
        footnotes.append(f"Inconsistency: {inconsistency.rationale}")
    if indirectness.decision > 0:
        footnotes.append(f"Indirectness: {indirectness.rationale}")
    if imprecision.decision > 0:
        footnotes.append(f"Imprecision: {imprecision.rationale}")
    if pub_bias.decision > 0:
        footnotes.append(f"Publication bias: {pub_bias.rationale}")

    return GradeResult(
        starting_certainty=starting_label,
        certainty=certainty_label,
        downgrade_count=total_down,
        upgrade_count=up,
        rob_decision=rob.decision,
        rob_rationale=rob.rationale,
        inconsistency_decision=inconsistency.decision,
        inconsistency_rationale=inconsistency.rationale,
        indirectness_decision=indirectness.decision,
        indirectness_rationale=indirectness.rationale,
        imprecision_decision=imprecision.decision,
        imprecision_rationale=imprecision.rationale,
        publication_bias_decision=pub_bias.decision,
        publication_bias_rationale=pub_bias.rationale,
        upgrade_reasons=upgrade_reasons,
        footnotes=footnotes,
        grade_symbol=grade_symbol,
    )
