"""Regression test for the stats module: cross-validated against numbers
independently computed and logged during the original project's Aug 11
sweep, derived from the paper's own published Fig. 13 counts (agentic
224/347, third-person 155/200). Matching those numbers exactly is a strong
correctness check. Ported unchanged from
model-forensic-research/tests/test_stats.py.
"""

import math

from stated_vs_revealed.stats import (
    equivalence_check,
    two_proportion_one_sided_z_test,
    wilson_ci,
)


def test_wilson_ci_matches_cowork_log_third_person():
    lo, hi = wilson_ci(155, 200)
    assert round(lo * 100, 1) == 71.2
    assert round(hi * 100, 1) == 82.7


def test_wilson_ci_matches_cowork_log_agentic():
    lo, hi = wilson_ci(224, 347)
    assert round(lo * 100, 1) == 59.4
    assert round(hi * 100, 1) == 69.4


def test_two_proportion_test_matches_cowork_log_A04():
    r = two_proportion_one_sided_z_test(successes_a=155, n_a=200, successes_b=224, n_b=347)
    assert round(r.rate_a * 100, 1) == 77.5
    assert round(r.rate_b * 100, 1) == 64.6
    assert round(r.diff * 100, 1) == 12.9
    assert round(r.se_diff * 100, 2) == 3.91
    assert round(r.z, 2) == 3.16
    assert round(2 * r.p_value_one_sided, 4) == 0.0016


def test_wilson_ci_matches_diff_se_from_manual_formula():
    r = two_proportion_one_sided_z_test(successes_a=155, n_a=200, successes_b=224, n_b=347)
    manual_se = math.sqrt(0.775 * 0.225 / 200 + (224 / 347) * (1 - 224 / 347) / 347)
    assert abs(r.se_diff - manual_se) < 1e-6


def test_equivalence_check_no_margin():
    assert equivalence_check(5.0, None) == "no_margin_prespecified"


def test_equivalence_check_within_margin():
    result = equivalence_check(3.0, margin_pp=10.0)
    assert "within_equivalence_margin" in result


def test_equivalence_check_outside_margin():
    result = equivalence_check(15.0, margin_pp=10.0)
    assert "outside_equivalence_margin" in result


def test_equivalence_check_is_symmetric_in_sign():
    assert equivalence_check(-15.0, margin_pp=10.0) == equivalence_check(15.0, margin_pp=10.0)
