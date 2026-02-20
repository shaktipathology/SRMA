"""
Compute Cohen's κ between two lists of screening labels.

Uses sklearn.metrics.cohen_kappa_score.
Returns None when κ is undefined (< 2 samples or only one class present).
"""
from __future__ import annotations

from typing import List, Optional

from sklearn.metrics import cohen_kappa_score


LABEL_ORDER = ["include", "exclude", "uncertain"]


def compute_kappa(
    agent1_labels: List[str],
    agent2_labels: List[str],
) -> Optional[float]:
    """
    Return Cohen's κ for the two label lists, or None if undefined.
    Both lists must have the same length.
    """
    if len(agent1_labels) < 2:
        return None
    # Need at least 2 distinct values across both lists combined
    combined = set(agent1_labels) | set(agent2_labels)
    if len(combined) < 2:
        return None
    try:
        kappa = cohen_kappa_score(agent1_labels, agent2_labels, labels=LABEL_ORDER)
        return round(float(kappa), 4)
    except Exception:
        return None
