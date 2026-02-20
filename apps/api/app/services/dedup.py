"""
Jaro-Winkler deduplication for a batch of papers.

Papers whose titles score >= THRESHOLD are treated as duplicates.
The first occurrence in the list is kept; subsequent near-matches are
flagged with the ID of the paper they duplicate.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from rapidfuzz.distance import JaroWinkler

THRESHOLD = 0.95  # similarity score above which titles are considered duplicates


def _normalise(title: Optional[str]) -> str:
    if not title:
        return ""
    return title.lower().strip()


def find_duplicates(
    papers: List[Tuple[uuid.UUID, Optional[str]]]
) -> Dict[uuid.UUID, Optional[uuid.UUID]]:
    """
    Given a list of (paper_id, title) pairs, return a dict mapping each
    paper_id to:
      - None  — this paper is kept (not a duplicate)
      - uuid  — the paper_id of the paper it duplicates
    """
    result: Dict[uuid.UUID, Optional[uuid.UUID]] = {}
    # IDs of papers already marked as originals, in order
    originals: List[Tuple[uuid.UUID, str]] = []

    for paper_id, raw_title in papers:
        norm = _normalise(raw_title)
        duplicate_of: Optional[uuid.UUID] = None

        if norm:  # skip empty titles — treat as unique
            for orig_id, orig_norm in originals:
                score = JaroWinkler.normalized_similarity(norm, orig_norm)
                if score >= THRESHOLD:
                    duplicate_of = orig_id
                    break

        if duplicate_of is None:
            originals.append((paper_id, norm))

        result[paper_id] = duplicate_of

    return result
