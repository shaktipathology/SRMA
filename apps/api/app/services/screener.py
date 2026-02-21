"""
Dual-agent title/abstract screener using Claude claude-sonnet-4-6.

Two agents run in parallel with deliberately different personas to reduce
correlated errors. Both return JSON with {label, reasoning}.
Labels: "include" | "exclude" | "uncertain"
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Optional, Tuple

import anthropic

from app.core.config import settings

MODEL = "claude-sonnet-4-6"

VALID_LABELS = {"include", "exclude", "uncertain"}

_AGENT1_SYSTEM = """\
You are Agent-1, a systematic review screener focused on clinical relevance.
Assess the paper below against the given inclusion criteria.

Respond ONLY with valid JSON — no markdown, no prose:
{"label": "include" | "exclude" | "uncertain", "reasoning": "<≤60 words>"}

Rules:
- "include"   → clearly meets population, intervention, and at least one outcome
- "exclude"   → clearly irrelevant (wrong population, intervention, or study type)
- "uncertain" → ambiguous abstract, missing information, or you are not sure
"""

_AGENT2_SYSTEM = """\
You are Agent-2, a systematic review screener focused on methodological rigour.
Assess the paper below against the given inclusion criteria.

Respond ONLY with valid JSON — no markdown, no prose:
{"label": "include" | "exclude" | "uncertain", "reasoning": "<≤60 words>"}

Rules:
- "include"   → study design meets requirements and sufficient methodological quality
- "exclude"   → wrong study design, duplicate, or clearly non-empirical
- "uncertain" → cannot determine design or quality from the abstract alone
"""


def _build_user_message(
    title: Optional[str],
    abstract: Optional[str],
    criteria: Optional[str],
) -> str:
    lines = []
    if criteria:
        lines.append(f"Inclusion criteria:\n{criteria}\n")
    lines.append(f"Title: {title or '(no title)'}")
    lines.append(f"Abstract: {abstract or '(no abstract)'}")
    return "\n".join(lines)


def _parse(text: str) -> Dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    data = json.loads(text)
    label = data.get("label", "uncertain").lower()
    if label not in VALID_LABELS:
        label = "uncertain"
    data["label"] = label
    return data


async def _call_agent(system: str, user_msg: str) -> Dict[str, Any]:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    resp = await client.messages.create(
        model=MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return _parse(resp.content[0].text)


async def screen_paper(
    title: Optional[str],
    abstract: Optional[str],
    criteria: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Run both agents in parallel.
    Returns (agent1_result, agent2_result) each with keys: label, reasoning.
    """
    user_msg = _build_user_message(title, abstract, criteria)
    agent1, agent2 = await asyncio.gather(
        _call_agent(_AGENT1_SYSTEM, user_msg),
        _call_agent(_AGENT2_SYSTEM, user_msg),
    )
    return agent1, agent2


_FT_AGENT1_SYSTEM = """\
You are Agent-1, a systematic review screener conducting full-text eligibility assessment.
You focus on clinical relevance: does this paper study the right population, intervention, and outcomes?

Read the provided full-text excerpt and assess against the inclusion criteria.

Respond ONLY with valid JSON — no markdown, no prose:
{"label": "include" | "exclude" | "uncertain", "reasoning": "<≤80 words>"}

Rules:
- "include"   → population, intervention, comparator, and at least one outcome clearly meet criteria
- "exclude"   → clearly fails at least one eligibility criterion (wrong population, intervention, outcome, or design)
- "uncertain" → key eligibility information ambiguous or not reported in this excerpt
"""

_FT_AGENT2_SYSTEM = """\
You are Agent-2, a systematic review screener conducting full-text eligibility assessment.
You focus on methodological validity: does this study design produce usable evidence?

Read the provided full-text excerpt and assess against the inclusion criteria.

Respond ONLY with valid JSON — no markdown, no prose:
{"label": "include" | "exclude" | "uncertain", "reasoning": "<≤80 words>"}

Rules:
- "include"   → study design (RCT, cohort, etc.) meets requirements; sample size and follow-up are adequate
- "exclude"   → wrong design, non-comparative, no usable effect estimate, or conference abstract only
- "uncertain" → design details not clearly stated in this excerpt
"""

# Maximum characters of full text sent to Claude (avoids excessive token use)
_FT_MAX_CHARS = 6_000


def _build_fulltext_message(
    title: Optional[str],
    full_text: str,
    criteria: Optional[str],
) -> str:
    lines = []
    if criteria:
        lines.append(f"Inclusion criteria:\n{criteria}\n")
    lines.append(f"Title: {title or '(no title)'}")
    # Truncate to avoid token overflow
    excerpt = full_text[:_FT_MAX_CHARS]
    if len(full_text) > _FT_MAX_CHARS:
        excerpt += "\n[... text truncated ...]"
    lines.append(f"\nFull-text excerpt:\n{excerpt}")
    return "\n".join(lines)


async def screen_fulltext_paper(
    title: Optional[str],
    full_text: str,
    criteria: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Full-text dual-agent screening. Uses longer prompts and up to 6 000 chars of text.
    Returns (agent1_result, agent2_result) each with keys: label, reasoning.
    """
    user_msg = _build_fulltext_message(title, full_text, criteria)
    agent1, agent2 = await asyncio.gather(
        _call_agent(_FT_AGENT1_SYSTEM, user_msg),
        _call_agent(_FT_AGENT2_SYSTEM, user_msg),
    )
    return agent1, agent2


def resolve_final_label(label1: str, label2: str) -> str:
    """
    Adjudication rule:
    - Agree → their label
    - Disagree with one "include" → "uncertain"
    - Both non-include → "exclude"
    """
    if label1 == label2:
        return label1
    if "include" in (label1, label2):
        return "uncertain"
    return "exclude"
