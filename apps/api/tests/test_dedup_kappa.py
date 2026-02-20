"""Unit tests for dedup and kappa services (no DB, no HTTP)."""
from __future__ import annotations

import uuid

import pytest

from app.services.dedup import find_duplicates
from app.services.kappa import compute_kappa
from app.services.screener import resolve_final_label

# These are sync unit tests — no asyncio mark needed


# ── Deduplication ──────────────────────────────────────────────────────────

def test_dedup_exact_match():
    ids = [uuid.uuid4(), uuid.uuid4()]
    title = "Effect of aspirin on cardiovascular outcomes"
    result = find_duplicates([(ids[0], title), (ids[1], title)])
    assert result[ids[0]] is None       # original kept
    assert result[ids[1]] == ids[0]     # duplicate of first


def test_dedup_near_match():
    ids = [uuid.uuid4(), uuid.uuid4()]
    t1 = "Effect of aspirin on cardiovascular outcomes: a meta-analysis"
    t2 = "Effect of aspirin on cardiovascular outcomes: a meta-analysi"   # one char short
    result = find_duplicates([(ids[0], t1), (ids[1], t2)])
    assert result[ids[0]] is None
    assert result[ids[1]] == ids[0]


def test_dedup_distinct_titles():
    ids = [uuid.uuid4(), uuid.uuid4()]
    result = find_duplicates([
        (ids[0], "Ketamine for depression"),
        (ids[1], "Mindfulness for anxiety"),
    ])
    assert result[ids[0]] is None
    assert result[ids[1]] is None


def test_dedup_empty_titles_treated_as_unique():
    ids = [uuid.uuid4(), uuid.uuid4()]
    result = find_duplicates([(ids[0], None), (ids[1], None)])
    # Empty titles are not compared — both treated as originals
    assert result[ids[0]] is None
    assert result[ids[1]] is None


def test_dedup_single_paper():
    pid = uuid.uuid4()
    result = find_duplicates([(pid, "Some title")])
    assert result[pid] is None


# ── Cohen's κ ──────────────────────────────────────────────────────────────

def test_kappa_perfect_agreement():
    a1 = ["include", "exclude", "include", "uncertain"]
    a2 = ["include", "exclude", "include", "uncertain"]
    k = compute_kappa(a1, a2)
    assert k == 1.0


def test_kappa_complete_disagreement():
    # Perfect cross-disagreement: a1 always opposite of a2 → κ = -1.0
    a1 = ["include", "exclude"]
    a2 = ["exclude", "include"]
    k = compute_kappa(a1, a2)
    assert k is not None
    assert k < 0.0   # worse than chance


def test_kappa_too_few_samples():
    k = compute_kappa(["include"], ["include"])
    assert k is None


def test_kappa_single_class():
    # Only one class in both → κ undefined
    k = compute_kappa(["include", "include", "include"], ["include", "include", "include"])
    assert k is None


def test_kappa_mixed():
    a1 = ["include", "exclude", "include", "exclude"]
    a2 = ["include", "include", "exclude", "exclude"]
    k = compute_kappa(a1, a2)
    assert k is not None
    assert -1.0 <= k <= 1.0


# ── Final label adjudication ───────────────────────────────────────────────

def test_resolve_agree_include():
    assert resolve_final_label("include", "include") == "include"


def test_resolve_agree_exclude():
    assert resolve_final_label("exclude", "exclude") == "exclude"


def test_resolve_agree_uncertain():
    assert resolve_final_label("uncertain", "uncertain") == "uncertain"


def test_resolve_include_exclude():
    assert resolve_final_label("include", "exclude") == "uncertain"


def test_resolve_include_uncertain():
    assert resolve_final_label("include", "uncertain") == "uncertain"


def test_resolve_exclude_uncertain():
    assert resolve_final_label("exclude", "uncertain") == "exclude"
