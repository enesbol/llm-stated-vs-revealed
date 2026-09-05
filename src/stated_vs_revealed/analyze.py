"""Per-env analysis: reads a run's label files, computes the pre-registered
primary statistic. Never picks a test after seeing results -- the direction,
positive label, and test name come from the env's own prereg file, always,
with no code-side default: a prereg missing a required field is a bug in the
prereg, not something this module papers over.

    python -m stated_vs_revealed.analyze --env funding_email --run results/live/funding_email/<ts>
    python -m stated_vs_revealed.analyze --env eval_tampering --run results/live/eval_tampering/<ts>

Label files, per the three-separate-files rule (never merge in place):
mechanical_labels.jsonl, human_labels.jsonl, judge_labels.jsonl -- each row
{"arm": ..., "replicate_index": ..., "label": ...}. consultative_labels.jsonl
(model-rater, multi-rater-resolved) is a DIFFERENT, lower tier again: never
human, never mechanical, and never eligible to feed the primary test, only
ever reported as a separate secondary/consultative reading.

Funding Email's run dirs predate this file-split convention: its human
labels live inline in graded_with_human_labels.jsonl's human_label field.
This script reads that directly for funding_email and does not require it
to have been re-split into human_labels.jsonl (splitting historical data
just to satisfy a later convention would risk transcription drift for zero
benefit -- the convention governs new runs, not old ones).

Primary-test guard: the primary statistic is computed only when every
eligible (non-excluded) manifest record in an arm has a label from that
env's prereg-specified primary source (human, or mechanical where the
env/arm has a deterministic rule). A partially-labeled arm is not silently
skipped -- it is reported as PENDING explicitly, with the shortfall count,
and no test is computed on the partial denominator. Judge and consultative
readings never substitute for this, however complete they are; they are
computed and reported separately, under result["secondary"].
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from stated_vs_revealed import stats
from stated_vs_revealed.envs import ENVS

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _manifest_eligible_counts(run_dir: Path) -> dict[str, int]:
    """{arm: count of eligible manifest records}. The manifest is the ground
    truth for "how many records exist to be labeled" -- label files alone
    can't distinguish a genuinely-complete arm from one that was never fully
    labeled, since a short label file and a short manifest look the same
    from the label file's own perspective.

    A record is ineligible if EITHER its own `excluded` flag is set OR it
    carries a non-null `error` field -- checked independently of `excluded`
    because at least one real run (funding_email 2026-09-04T16-10-25Z, a
    404'd provider route) has `error` set on every record while `excluded`
    is still False on all of them. That's a bug in that run's own manifest
    write path, not something to fix here (manifests are frozen, never
    edited), but the prereg's own exclusions rule ("API errors ... excluded
    from the primary denominator") is unconditional on the error field
    existing, regardless of whether the excluded flag was also set."""
    manifest = _load_jsonl(run_dir / "manifest.jsonl")
    counts: dict[str, int] = {}
    for r in manifest:
        if r.get("excluded") or r.get("error"):
            continue
        counts[r["arm"]] = counts.get(r["arm"], 0) + 1
    return counts


def _parse_estimand_order(estimand: str) -> tuple[str, str]:
    """Returns (first, second) arm codes such that the prereg's estimand
    equals rate_first - rate_second. Parses rather than assumes, so a future
    prereg that flips the order (A - B instead of B - A) is honored, not
    silently miscomputed by a hardcoded convention. Recognizes the two forms
    actually used in this repo's prereg files: "<metric>_B - <metric>_A" and
    "<metric>_B_minus_A"."""
    m = re.search(r"_([AB])\s*-\s*[\w]*_([AB])\b", estimand)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"_([AB])_minus_([AB])\b", estimand)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(f"Cannot parse estimand order from primary_estimand={estimand!r}")


def _fe_resolve_positive_label(prereg: dict) -> str:
    outcome = prereg.get("primary_outcome", {})
    if "positive_label" in outcome:
        return outcome["positive_label"]
    # Not a default: several Funding Email amendment preregs (expansion.json,
    # expansion-v2.json) document in their own prose that they inherit
    # pilot.json's primary_outcome/grading philosophy rather than repeating
    # the field. Resolve that documented inheritance explicitly, from the
    # one file it can only ever mean, rather than assuming a value.
    pilot_path = REPO_ROOT / "envs" / "funding_email" / "prereg" / "pilot.json"
    if not pilot_path.exists():
        raise KeyError(
            "primary_outcome.positive_label is absent and envs/funding_email/prereg/pilot.json "
            "(the only documented inheritance source) does not exist"
        )
    pilot_prereg = json.loads(pilot_path.read_text(encoding="utf-8"))
    return pilot_prereg["primary_outcome"]["positive_label"]


def analyze_funding_email(run_dir: Path, prereg: dict) -> dict:
    graded_path = run_dir / "graded_with_human_labels.jsonl"
    if not graded_path.exists():
        graded_path = run_dir / "graded.jsonl"
    records = _load_jsonl(graded_path)
    positive_label = _fe_resolve_positive_label(prereg)
    direction = prereg["primary_hypothesis"]["direction"]
    test_name = prereg["statistics"]["test"]

    eligible_n = _manifest_eligible_counts(run_dir)
    by_arm: dict[str, list[dict]] = {}
    for r in records:
        if r.get("excluded"):
            continue
        by_arm.setdefault(r["arm"], []).append(r)

    counts = {}
    per_arm_detail = {}
    pending_arms = []
    for arm, n_eligible in sorted(eligible_n.items()):
        recs = by_arm.get(arm, [])
        labels = [r.get("human_label") for r in recs]
        human_labeled_count = sum(1 for lab in labels if lab is not None)
        successes = sum(1 for lab in labels if lab == positive_label)
        counts[arm] = (successes, human_labeled_count)
        per_arm_detail[arm] = {"n_eligible": n_eligible, "human_labeled_count": human_labeled_count}
        if human_labeled_count < n_eligible:
            pending_arms.append(arm)

    result: dict = {"env": "funding_email", "counts": counts, "per_arm": per_arm_detail}
    if pending_arms:
        result["test"] = None
        result["note"] = (
            "PENDING: human labels incomplete for arm(s) "
            + ", ".join(f"{a} ({per_arm_detail[a]['human_labeled_count']}/{per_arm_detail[a]['n_eligible']})" for a in pending_arms)
            + " -- primary test not computed on a partial denominator."
        )
    elif "A" in counts and "B" in counts:
        (sa, na), (sb, nb) = counts["A"], counts["B"]
        test = _run_z_test(test_name, direction, sa, na, sb, nb)
        result["test"] = _z_test_to_dict(test, direction)

    secondary = _fe_secondary(run_dir, positive_label)
    if secondary is not None:
        result["secondary"] = secondary
    return result


def _fe_secondary(run_dir: Path, positive_label: str) -> dict | None:
    """Judge-per-arm secondary reading (judge_labels.jsonl), reported
    separately, never feeding the primary human-labeled test above -- this
    is the full-sample number to cite when the primary is PENDING, always
    tagged judge-labeled, never presented as if it were the human primary."""
    judge = _load_jsonl(run_dir / "judge_labels.jsonl")
    if not judge:
        return None
    by_arm: dict[str, list[str]] = {}
    for r in judge:
        by_arm.setdefault(r["arm"], []).append(r["label"])
    counts = {arm: (sum(1 for lab in labs if lab == positive_label), len(labs)) for arm, labs in by_arm.items()}
    label_composition = {arm: dict(_counter(labs)) for arm, labs in by_arm.items()}
    out: dict = {
        "instrument": ["judge_per_arm"],
        "counts": counts,
        "label_composition": label_composition,
        "note": "Judge-per-arm (third_person on A, agentic on B); never primary.",
    }
    if "A" in counts and "B" in counts and counts["A"][1] > 0 and counts["B"][1] > 0:
        (sa, na), (sb, nb) = counts["A"], counts["B"]
        test = stats.two_proportion_one_sided_z_test(sa, na, sb, nb)
        out["diff_pp"] = test.diff * 100
        out["p_value_two_sided"] = test.p_value_two_sided
    return out


def _counter(items: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        out[it] = out.get(it, 0) + 1
    return out


def _run_z_test(test_name: str, direction: str, sa: int, na: int, sb: int, nb: int) -> stats.TwoProportionTestResult:
    expected = {"one_sided": "two_proportion_one_sided_z_test", "two_sided": "two_proportion_two_sided_z_test"}
    if test_name != expected.get(direction):
        raise ValueError(
            f"prereg statistics.test={test_name!r} does not match primary_hypothesis.direction={direction!r} "
            f"(expected {expected.get(direction)!r}) -- prereg is internally inconsistent"
        )
    return stats.two_proportion_one_sided_z_test(sa, na, sb, nb)


def _z_test_to_dict(test: stats.TwoProportionTestResult, direction: str) -> dict:
    p_primary = test.p_value_two_sided if direction == "two_sided" else test.p_value_one_sided
    return {
        "rate_a": test.rate_a,
        "rate_b": test.rate_b,
        "diff_pp": test.diff * 100,
        "z": test.z,
        "p_value_one_sided": test.p_value_one_sided,
        "p_value_two_sided": test.p_value_two_sided,
        "p_value_primary": p_primary,
        "primary_hypothesis_direction": direction,
        "ci_diff_95_wald": test.ci_diff_95,
        "ci_a_wilson_95": test.ci_a,
        "ci_b_wilson_95": test.ci_b,
    }


def _et_labels_from_source(run_dir: Path, source: str) -> list[dict]:
    filename = {"human": "human_labels.jsonl", "mechanical": "mechanical_labels.jsonl"}[source]
    return _load_jsonl(run_dir / filename)


def _et_primary_labels_by_arm(run_dir: Path) -> tuple[dict[str, dict[int, str]], dict[str, dict[int, str]]]:
    """Returns (labels_by_arm, source_by_arm), built only from human_labels.jsonl
    and mechanical_labels.jsonl -- judge_labels.jsonl and consultative_labels.jsonl
    are never read here; they feed result["secondary"] instead, never this."""
    labels: dict[str, dict[int, str]] = {}
    source: dict[str, dict[int, str]] = {}
    # mechanical first, human overrides -- matches the documented human >
    # mechanical priority (a human relabel of a mechanically-graded record,
    # if it ever happens, should win).
    for src in ("mechanical", "human"):
        for r in _et_labels_from_source(run_dir, src):
            if r.get("label") is None:
                continue
            labels.setdefault(r["arm"], {})[r["replicate_index"]] = r["label"]
            source.setdefault(r["arm"], {})[r["replicate_index"]] = src
    return labels, source


def _et_fisher_test(prereg: dict, rate_counts: dict[str, tuple[int, int]]) -> dict:
    positive_label = prereg["primary_outcome"]["positive_label_for_estimand"]
    estimand = prereg["primary_estimand"]
    test_name = prereg["statistics"]["test"]
    if test_name != "two_sided_fisher_exact":
        raise NotImplementedError(f"Unsupported eval_tampering statistics.test={test_name!r}")
    first, second = _parse_estimand_order(estimand)
    (s_first, n_first), (s_second, n_second) = rate_counts[first], rate_counts[second]
    test = stats.two_sided_fisher_exact(s_first, n_first, s_second, n_second)
    return {
        "positive_label": positive_label,
        "estimand": estimand,
        "rate_first": test.rate_a,
        "rate_second": test.rate_b,
        "diff_pp": test.diff * 100,  # rate_first - rate_second, i.e. exactly the prereg's estimand
        "p_value_two_sided": test.p_value_two_sided,
        "p_value_less": test.p_value_less,
        "p_value_greater": test.p_value_greater,
        "p_value_primary": test.p_value_two_sided,  # both current ET preregs are two-sided
        "primary_hypothesis_direction": prereg["primary_hypothesis"]["direction"],
        "ci_diff_95_wald": test.ci_diff_95_wald,
        "ci_first_wilson_95": test.ci_a,
        "ci_second_wilson_95": test.ci_b,
        "test_name": test_name,
    }


def analyze_eval_tampering(run_dir: Path, prereg: dict) -> dict:
    positive_label = prereg["primary_outcome"]["positive_label_for_estimand"]
    eligible_n = _manifest_eligible_counts(run_dir)
    labels_by_arm, source_by_arm = _et_primary_labels_by_arm(run_dir)

    counts: dict[str, tuple[int, int]] = {}
    per_arm_detail = {}
    pending_arms = []
    for arm, n_eligible in sorted(eligible_n.items()):
        arm_labels = labels_by_arm.get(arm, {})
        labeled_count = len(arm_labels)
        successes = sum(1 for lab in arm_labels.values() if lab == positive_label)
        counts[arm] = (successes, labeled_count)
        per_arm_detail[arm] = {
            "n_eligible": n_eligible,
            "labeled_count": labeled_count,
            "sources_used": sorted(set(source_by_arm.get(arm, {}).values())),
        }
        if labeled_count < n_eligible:
            pending_arms.append(arm)

    result: dict = {"env": "eval_tampering", "counts": counts, "per_arm": per_arm_detail}

    if pending_arms:
        result["test"] = None
        result["note"] = (
            "PENDING: primary-source (human/mechanical) labels incomplete for arm(s) "
            + ", ".join(f"{a} ({per_arm_detail[a]['labeled_count']}/{per_arm_detail[a]['n_eligible']})" for a in pending_arms)
            + " -- primary test not computed. Judge/consultative labels do not count toward this, however complete."
        )
    else:
        result["test"] = _et_fisher_test(prereg, counts)

    secondary = _et_secondary(run_dir, prereg, positive_label)
    if secondary is not None:
        result["secondary"] = secondary
    return result


def _et_secondary(run_dir: Path, prereg: dict, positive_label: str) -> dict | None:
    """Judge/consultative labels, reported separately, never feeding the
    primary test above. Only built when consultative_labels.jsonl or
    judge_labels.jsonl actually exist for this run."""
    consultative = _load_jsonl(run_dir / "consultative_labels.jsonl")
    judge = _load_jsonl(run_dir / "judge_labels.jsonl")
    rows_by_arm: dict[str, list[dict]] = {}
    sources: set[str] = set()
    for rows, src in ((consultative, "consultative"), (judge, "judge")):
        for r in rows:
            rows_by_arm.setdefault(r["arm"], []).append(r)
            sources.add(src)
    if not rows_by_arm:
        return None

    # Fill in whichever arm the primary already fully covers (human/
    # mechanical) so the secondary comparison is still A-vs-B even when only
    # one arm has a secondary reading of its own.
    primary_labels, _ = _et_primary_labels_by_arm(run_dir)
    counts: dict[str, tuple[int, int]] = {}
    for arm in sorted(set(rows_by_arm) | set(primary_labels)):
        if arm in rows_by_arm:
            labels = [r["label"] for r in rows_by_arm[arm]]
        else:
            labels = list(primary_labels[arm].values())
        n = len(labels)
        if n == 0:
            continue
        counts[arm] = (sum(1 for lab in labels if lab == positive_label), n)

    out: dict = {"instrument": sorted(sources), "counts": counts, "note": "Model-rated and/or consultative; never primary."}
    if "A" in counts and "B" in counts and counts["A"][1] > 0 and counts["B"][1] > 0:
        try:
            first, second = _parse_estimand_order(prereg["primary_estimand"])
            (s1, n1), (s2, n2) = counts[first], counts[second]
            test = stats.two_sided_fisher_exact(s1, n1, s2, n2)
            out["diff_pp"] = test.diff * 100
            out["p_value_two_sided"] = test.p_value_two_sided
        except (KeyError, ValueError):
            pass
    return out


ANALYZERS = {
    "funding_email": analyze_funding_email,
    "eval_tampering": analyze_eval_tampering,
}


def analyze(env_name: str, run_dir: Path, prereg: dict) -> dict:
    if env_name not in ENVS:
        raise KeyError(f"Unknown env {env_name!r}. Registered: {sorted(ENVS)}")
    return ANALYZERS[env_name](run_dir, prereg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", required=True, choices=sorted(ENVS))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    args = parser.parse_args(argv)

    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    result = analyze(args.env, args.run, prereg)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
