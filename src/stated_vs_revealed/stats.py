"""Pre-specified statistics only -- the test named in a prereg is what runs,
never chosen after seeing results. Environment-agnostic: every function here
takes plain counts, not env-specific record shapes (that mapping lives in
analyze.py). Ported from model-forensic-research/src/ours/analyze_results.py,
with the funding_email-specific pieces (classify_complete_email, the
agentic/third-person label mapping) split out to envs/funding_email.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = _z_for_confidence(confidence)
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    half_width = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    lo = (centre - half_width) / denom
    hi = (centre + half_width) / denom
    return (max(0.0, lo), min(1.0, hi))


def _z_for_confidence(confidence: float) -> float:
    from scipy.stats import norm

    return float(norm.ppf(1 - (1 - confidence) / 2))


@dataclass(frozen=True)
class TwoProportionTestResult:
    successes_a: int
    n_a: int
    successes_b: int
    n_b: int
    rate_a: float
    rate_b: float
    diff: float  # rate_a - rate_b
    se_diff: float
    z: float
    p_value_one_sided: float
    p_value_two_sided: float
    ci_diff_95: tuple[float, float]  # unpooled-SE 95% Wald CI on (rate_a - rate_b)
    ci_a: tuple[float, float]
    ci_b: tuple[float, float]


def two_proportion_one_sided_z_test(
    successes_a: int, n_a: int, successes_b: int, n_b: int
) -> TwoProportionTestResult:
    """H1: rate_b < rate_a. One-sided by convention; p_value_two_sided is
    also always computed so a caller reading a two_sided prereg direction
    never has to re-derive it."""
    from scipy.stats import norm

    rate_a = successes_a / n_a
    rate_b = successes_b / n_b
    pooled = (successes_a + successes_b) / (n_a + n_b)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    diff = rate_a - rate_b
    z = diff / se_pooled if se_pooled > 0 else float("nan")
    p_one_sided = float(1 - norm.cdf(z)) if not math.isnan(z) else float("nan")
    p_two_sided = float(2 * (1 - norm.cdf(abs(z)))) if not math.isnan(z) else float("nan")
    se_diff = math.sqrt(rate_a * (1 - rate_a) / n_a + rate_b * (1 - rate_b) / n_b)
    z_crit = float(norm.ppf(0.975))
    ci_diff = (diff - z_crit * se_diff, diff + z_crit * se_diff)
    return TwoProportionTestResult(
        successes_a=successes_a,
        n_a=n_a,
        successes_b=successes_b,
        n_b=n_b,
        rate_a=rate_a,
        rate_b=rate_b,
        diff=diff,
        se_diff=se_diff,
        z=z,
        p_value_one_sided=p_one_sided,
        p_value_two_sided=p_two_sided,
        ci_diff_95=ci_diff,
        ci_a=wilson_ci(successes_a, n_a),
        ci_b=wilson_ci(successes_b, n_b),
    )


def equivalence_check(diff_pp: float, margin_pp: float | None) -> str:
    if margin_pp is None:
        return "no_margin_prespecified"
    if abs(diff_pp) < margin_pp:
        return "within_equivalence_margin (format is not the driver)"
    return "outside_equivalence_margin (format plausibly explains part of the gap)"


def judge_agreement_rate(judge_labels: list, human_labels: list) -> float | None:
    """Fraction of pairs where both a judge label and a human label exist and
    agree. None (not NaN) when nothing is labeled yet."""
    pairs = [(j, h) for j, h in zip(judge_labels, human_labels) if j is not None and h is not None]
    if not pairs:
        return None
    return sum(1 for j, h in pairs if j == h) / len(pairs)


def cohens_kappa(labels_a: list, labels_b: list) -> float | None:
    """Simple unweighted Cohen's kappa over paired categorical labels,
    ignoring pairs where either side is None."""
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return None
    categories = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    confusion = [[0] * k for _ in range(k)]
    for a, b in pairs:
        confusion[idx[a]][idx[b]] += 1
    po = sum(confusion[i][i] for i in range(k)) / n
    row_marg = [sum(confusion[i]) / n for i in range(k)]
    col_marg = [sum(confusion[i][j] for i in range(k)) / n for j in range(k)]
    pe = sum(row_marg[i] * col_marg[i] for i in range(k))
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)
