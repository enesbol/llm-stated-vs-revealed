"""Exact and normalized duplicate detection within an arm, with a decision rule.

Detection alone isn't a policy (see CLAUDE.md rule 8): every duplicate is
excluded and re-sampled once; if the post-resample duplicate rate is still at
or above the configured kill threshold, that's reported, not silently
resampled away.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


def normalize(text: str) -> str:
    """Whitespace/casing-collapsed form used for the 'near-duplicate' check."""
    return re.sub(r"\s+", " ", text.strip().lower())


@dataclass(frozen=True)
class DuplicateReport:
    arm: str
    n: int
    exact_duplicate_indices: list[int]
    normalized_duplicate_indices: list[int]  # superset of exact, includes near-dupes
    duplicate_rate: float


def _duplicate_indices(texts: list[str], key) -> list[int]:
    """Indices of every sample whose key collides with an EARLIER sample's key
    (the first occurrence of a value is not itself flagged as a duplicate)."""
    seen: Counter[str] = Counter()
    flagged: list[int] = []
    for i, t in enumerate(texts):
        k = key(t)
        if seen[k] > 0:
            flagged.append(i)
        seen[k] += 1
    return flagged


def detect(arm: str, texts: list[str]) -> DuplicateReport:
    exact = _duplicate_indices(texts, lambda t: t)
    normalized = _duplicate_indices(texts, normalize)
    n = len(texts)
    rate = (len(normalized) / n) if n else 0.0
    return DuplicateReport(
        arm=arm,
        n=n,
        exact_duplicate_indices=exact,
        normalized_duplicate_indices=normalized,
        duplicate_rate=rate,
    )


def over_threshold(report: DuplicateReport, kill_threshold_frac: float) -> bool:
    return report.duplicate_rate >= kill_threshold_frac
