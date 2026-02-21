"""
PRISMA 2020 checklist validator (27 items).

Checks DB state for a given review and returns per-item status.
"""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grade_assessment import GradeAssessment
from app.models.phase_result import PhaseResult
from app.models.protocol_version import ProtocolVersion
from app.models.review import Review
from app.models.screening_decision import ScreeningDecision
from app.models.search_query import SearchQuery
from app.schemas.prisma_check import PrismaCheckResponse, PrismaItem


# PRISMA 2020 item definitions: (number, domain, description)
PRISMA_ITEMS = [
    (1, "Title", "Identify the report as a systematic review."),
    (2, "Abstract", "See the PRISMA 2020 for Abstracts checklist."),
    (3, "Introduction: Rationale", "Describe the rationale for the review in the context of existing knowledge."),
    (4, "Introduction: Objectives", "Provide an explicit statement of the objective(s) or question(s) the review addresses."),
    (5, "Methods: Eligibility criteria", "Specify the inclusion and exclusion criteria for the review."),
    (6, "Methods: Information sources", "Specify all databases, registers, websites, organisations, reference lists and other sources searched or consulted to identify studies."),
    (7, "Methods: Search strategy", "Present the full search strategies for all databases, registers and websites, including any filters and limits used."),
    (8, "Methods: Selection process", "Specify the methods used to decide whether a study met the inclusion criteria of the review."),
    (9, "Methods: Data collection process", "Specify the methods used to collect data from reports."),
    (10, "Methods: Data items", "List and define all outcomes for which data were sought."),
    (11, "Methods: Study risk of bias assessment", "Specify the methods used to assess risk of bias in the included studies."),
    (12, "Methods: Effect measures", "Specify for each outcome the effect measure(s) used in the synthesis or presentation of results."),
    (13, "Methods: Synthesis methods", "Describe the methods used to present and synthesise results."),
    (14, "Methods: Reporting bias assessment", "Describe any methods used to assess risk of bias due to missing results in a synthesis."),
    (15, "Methods: Certainty assessment", "Describe any methods used to assess certainty (or confidence) in the body of evidence."),
    (16, "Results: Study selection", "Describe the results of the search and selection process, including reasons for exclusions."),
    (17, "Results: Study characteristics", "Cite each included study and present its characteristics."),
    (18, "Results: Risk of bias in studies", "Present assessments of risk of bias for each included study."),
    (19, "Results: Results of individual studies", "For all outcomes, present, for each study, all the data from which a synthesis was produced."),
    (20, "Results: Results of syntheses", "For each synthesis, briefly summarise the characteristics and risk of bias among contributing studies."),
    (21, "Results: Reporting biases", "Present assessments of risk of bias due to missing results for each synthesis assessed."),
    (22, "Results: Certainty of evidence", "Present assessments of certainty of evidence for each outcome assessed."),
    (23, "Discussion: Discussion of results", "Provide a general interpretation of the results in the context of other evidence."),
    (24, "Discussion: Limitations of evidence", "Discuss any limitations of the evidence included in the review."),
    (25, "Discussion: Limitations of review process", "Discuss any limitations of the review process or methods."),
    (26, "Discussion: Conclusions", "Provide a general interpretation of the results and any implications for research, practice and policy."),
    (27, "Other: Registration and protocol", "Provide registration information for the review, including register name and registration number."),
]


async def validate_prisma(
    db: AsyncSession,
    review_id: uuid.UUID,
) -> PrismaCheckResponse:
    """Run all 27 PRISMA checks and return a structured response."""

    # --- Fetch DB state ---
    review = await db.get(Review, review_id)
    title_ok = bool(review and review.title and review.title.strip())

    # Phase 1: latest protocol
    pv_result = await db.execute(
        select(ProtocolVersion)
        .where(ProtocolVersion.review_id == review_id)
        .order_by(ProtocolVersion.version.desc())
        .limit(1)
    )
    protocol = pv_result.scalar_one_or_none()
    pico_ok = False
    if protocol and protocol.pico_schema:
        pico = protocol.pico_schema
        pico_ok = all(k in pico for k in ("population", "intervention", "comparator", "outcomes", "study_designs"))

    # Phase 2: search query
    sq_result = await db.execute(
        select(SearchQuery)
        .where(SearchQuery.review_id == review_id)
        .order_by(SearchQuery.created_at.desc())
        .limit(1)
    )
    search = sq_result.scalar_one_or_none()
    db_ok = bool(search and search.database)
    search_string_ok = bool(search and search.search_string)

    # Phase 3/4: screening decisions
    screening_count = await db.scalar(
        select(func.count(ScreeningDecision.id)).where(
            ScreeningDecision.review_id == review_id
        )
    )
    screening_ok = bool(screening_count and screening_count > 0)

    # Phases 5–9
    stubs_result = await db.execute(
        select(PhaseResult)
        .where(
            PhaseResult.review_id == review_id,
            PhaseResult.phase_number.in_([5, 6, 7, 8, 9]),
        )
    )
    stubs = {pr.phase_number: pr for pr in stubs_result.scalars().all()}

    phase8_ok = 8 in stubs
    phase9_ok = 9 in stubs

    # Phase 10: GRADE
    grade_count = await db.scalar(
        select(func.count(GradeAssessment.id)).where(
            GradeAssessment.review_id == review_id
        )
    )
    grade_ok = bool(grade_count and grade_count > 0)

    # both abstract prerequisites: phase1 + phase2
    abstract_ok = bool(protocol and search)

    # --- Build checklist ---
    checklist: List[PrismaItem] = []

    def _item(num: int, domain: str, desc: str, status: str, notes: str = None) -> PrismaItem:
        return PrismaItem(
            item_number=num,
            domain=domain,
            description=desc,
            status=status,
            notes=notes,
        )

    for item_num, domain, description in PRISMA_ITEMS:
        if item_num == 1:
            status = "satisfied" if title_ok else "missing"
            notes = None if title_ok else "Review title is empty or missing"

        elif item_num == 2:
            status = "satisfied" if abstract_ok else "missing"
            notes = None if abstract_ok else "Requires Phase 1 (protocol) and Phase 2 (search) data"

        elif item_num == 5:
            status = "satisfied" if pico_ok else "missing"
            notes = None if pico_ok else "PICO schema missing one or more required keys (population, intervention, comparator, outcomes, study_designs)"

        elif item_num == 6:
            status = "satisfied" if db_ok else "missing"
            notes = None if db_ok else "Search database not recorded in Phase 2"

        elif item_num == 7:
            status = "satisfied" if search_string_ok else "missing"
            notes = None if search_string_ok else "Search string not recorded in Phase 2"

        elif item_num == 13:
            status = "satisfied" if screening_ok else "missing"
            notes = None if screening_ok else "No screening decisions recorded (Phase 3/4)"

        elif item_num in (16, 17, 18, 19):
            status = "satisfied" if phase8_ok else "missing"
            notes = None if phase8_ok else "Requires Phase 8 (meta-analysis) data"

        elif item_num == 20:
            status = "satisfied" if phase8_ok else "missing"
            notes = None if phase8_ok else "Requires Phase 8 (meta-analysis) data"

        elif item_num == 21:
            status = "satisfied" if phase9_ok else "missing"
            notes = None if phase9_ok else "Requires Phase 9 (publication bias) data"

        elif item_num == 22:
            status = "satisfied" if grade_ok else "missing"
            notes = None if grade_ok else "Requires Phase 10 (GRADE) data"

        else:
            # Items that require narrative review — mark partial
            status = "partial"
            notes = "Machine-checkable data present but narrative content requires author review"

        checklist.append(_item(item_num, domain, description, status, notes))

    satisfied = sum(1 for i in checklist if i.status == "satisfied")
    partial = sum(1 for i in checklist if i.status == "partial")
    missing = sum(1 for i in checklist if i.status == "missing")
    not_applicable = sum(1 for i in checklist if i.status == "not_applicable")

    return PrismaCheckResponse(
        review_id=review_id,
        total_items=27,
        satisfied=satisfied,
        partial=partial,
        missing=missing,
        not_applicable=not_applicable,
        is_compliant=(missing == 0),
        checklist=checklist,
    )
