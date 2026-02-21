from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import anthropic

from app.core.config import settings

MODEL = "claude-sonnet-4-6"

PICO_SYSTEM = """\
You are a systematic-review methodologist. When given a research question, extract PICO components and return ONLY valid JSON — no markdown, no prose, no code fences.

Schema:
{
  "population": "<string>",
  "intervention": "<string>",
  "comparator": "<string>",
  "outcomes": ["<string>", ...],
  "study_designs": ["<string>", ...]
}

Rules:
- outcomes and study_designs must be non-empty arrays
- If comparator is not stated, use "any / placebo / usual care"
- If study designs are not specified, default to ["randomised controlled trial", "systematic review"]
"""

SEARCH_SYSTEM = """\
You are a biomedical librarian with expertise in PubMed search strategy design.
Given a PICO schema, construct an optimal PubMed boolean search string using MeSH terms and free-text synonyms.

Return ONLY valid JSON — no markdown, no prose, no code fences.

Schema:
{
  "search_string": "<valid PubMed boolean string>",
  "rationale": "<1-2 sentence explanation>"
}

Rules:
- Use field tags: [MeSH Terms], [Title/Abstract], [tw]
- Combine population AND intervention/comparator with AND
- Use OR for synonyms within each concept block
- Wrap each concept block in parentheses
"""


def _parse_json_from_response(text: str) -> Dict[str, Any]:
    """Extract JSON from Claude response, handling any stray markdown."""
    # Strip optional code fence
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


async def extract_pico(research_question: str) -> Dict[str, Any]:
    """Call Claude to extract PICO components from a research question."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=PICO_SYSTEM,
        messages=[{"role": "user", "content": research_question}],
    )
    text = response.content[0].text
    pico = _parse_json_from_response(text)
    return pico


async def build_pubmed_search(pico_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Call Claude to construct a PubMed boolean search string from PICO."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    user_content = f"PICO:\n{json.dumps(pico_schema, indent=2)}"
    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SEARCH_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    result = _parse_json_from_response(text)
    return result


METHODS_NARRATIVE_SYSTEM = """\
You are an academic medical writer. Write 2–3 concise sentences describing the study selection methods
for a systematic review based on the provided PICO and search strategy. Use passive voice, past tense.
Return plain text only — no JSON, no markdown.
"""

RESULTS_NARRATIVE_SYSTEM = """\
You are an academic medical writer. Write 2–3 concise sentences summarising the study selection results
and certainty of evidence for a systematic review. Use passive voice, past tense.
Return plain text only — no JSON, no markdown.
"""


async def generate_methods_narrative(pico: Dict[str, Any], search_string: str) -> str:
    """Call Claude to generate a Methods narrative for study selection."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    user_content = (
        f"PICO:\n{json.dumps(pico, indent=2)}\n\n"
        f"Search string:\n{search_string}"
    )
    response = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=METHODS_NARRATIVE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()


async def generate_results_narrative(
    screening_counts: Dict[str, Any],
    grade_outcomes: List[Dict[str, Any]],
) -> str:
    """Call Claude to generate a Results narrative summarising screening and GRADE."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    user_content = (
        f"Screening counts:\n{json.dumps(screening_counts, indent=2)}\n\n"
        f"GRADE outcomes:\n{json.dumps(grade_outcomes, indent=2)}"
    )
    response = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=RESULTS_NARRATIVE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()
