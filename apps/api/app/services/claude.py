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


EXTRACTION_SYSTEM = """\
You are a systematic review data extractor. Extract structured data from the paper provided.

Return ONLY valid JSON — no markdown, no prose, no code fences.

Schema:
{
  "study_design": "<string: e.g. randomised controlled trial, cohort study>",
  "population": "<string: brief description>",
  "n_total": <integer or null>,
  "n_intervention": <integer or null>,
  "n_control": <integer or null>,
  "mean_age": <float or null>,
  "percent_female": <float or null>,
  "setting": "<string or null>",
  "country": "<string or null>",
  "intervention": "<string>",
  "comparator": "<string>",
  "follow_up_months": <float or null>,
  "outcomes": [
    {
      "name": "<string>",
      "measure_type": "<OR|RR|HR|MD|SMD|other>",
      "value": <float or null>,
      "ci_lower": <float or null>,
      "ci_upper": <float or null>,
      "p_value": <float or null>,
      "time_point": "<string or null>"
    }
  ],
  "notes": "<string or null>"
}

Rules:
- Use null for any field that cannot be determined from the text
- outcomes must be a list (may be empty if no quantitative results found)
- Extract all outcomes reported, not just the primary outcome
"""

# Maximum characters of paper text sent for extraction
_EXTRACT_MAX_CHARS = 8_000


async def extract_paper_data(
    title: Optional[str],
    full_text: str,
    extraction_template: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call Claude to extract structured data from a paper's full text.
    Returns a dict matching the extraction schema above.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)

    excerpt = full_text[:_EXTRACT_MAX_CHARS]
    if len(full_text) > _EXTRACT_MAX_CHARS:
        excerpt += "\n[... text truncated ...]"

    lines = []
    if extraction_template:
        lines.append(f"Additional extraction instructions:\n{extraction_template}\n")
    lines.append(f"Title: {title or '(no title)'}")
    lines.append(f"\nFull-text excerpt:\n{excerpt}")
    user_content = "\n".join(lines)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    return _parse_json_from_response(text)
