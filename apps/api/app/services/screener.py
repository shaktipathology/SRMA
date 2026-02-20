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
