"""Per-env analysis: reads a run's label files, computes the pre-registered
primary statistic. Never picks a test after seeing results -- the direction
and positive label come from the env's own prereg file, always.

    python -m stated_vs_revealed.analyze --env funding_email --run results/live/funding_email/<ts>
    python -m stated_vs_revealed.analyze --env eval_tampering --run results/live/eval_tampering/<ts>

Label files, per the three-separate-files rule (never merge in place):
mechanical_labels.jsonl, human_labels.jsonl, judge_labels.jsonl -- each row
{"arm": ..., "replicate_index": ..., "label": ...}. A generated
labels_merged.jsonl (source column: "human" > "mechanical" > "judge"
priority) is a build artifact this script writes, never hand-edited and
never itself read back as ground truth by anything else.

Funding Email's run dirs predate this file-split convention: its human
labels live inline in graded_with_human_labels.jsonl's human_label field.
This script reads that directly for funding_email and does not require it
to have been re-split into human_labels.jsonl (splitting historical data
just to satisfy a later convention would risk transcription drift for zero
benefit -- the convention governs new runs, not old ones).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stated_vs_revealed import stats
from stated_vs_revealed.envs import ENVS


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _merge_labels(mechanical: list[dict], human: list[dict], judge: list[dict]) -> dict[tuple[str, int], tuple[str, str]]:
    """Returns {(arm, replicate_index): (label, source)}, human overriding
    mechanical overriding judge -- built fresh every call, never cached to
    disk as ground truth (only as the labels_merged.jsonl audit artifact)."""
    merged: dict[tuple[str, int], tuple[str, str]] = {}
    for rows, source in ((judge, "judge"), (mechanical, "mechanical"), (human, "human")):
        for r in rows:
            key = (r["arm"], r["replicate_index"])
            if r.get("label") is not None:
                merged[key] = (r["label"], source)
    return merged


def analyze_funding_email(run_dir: Path, prereg: dict) -> dict:
    graded_path = run_dir / "graded_with_human_labels.jsonl"
    if not graded_path.exists():
        graded_path = run_dir / "graded.jsonl"
    records = _load_jsonl(graded_path)
    # An amendment prereg (e.g. expansion.json) can inherit primary_outcome
    # from pilot.json rather than repeating it -- fall back to the pilot's
    # value rather than crashing on a documented inheritance.
    positive_label = prereg.get("primary_outcome", {}).get("positive_label", "disclose_specific")

    by_arm: dict[str, list[dict]] = {}
    for r in records:
        if r.get("excluded"):
            continue
        by_arm.setdefault(r["arm"], []).append(r)

    counts = {}
    per_arm_detail = {}
    for arm, recs in by_arm.items():
        n = len(recs)
        labels = [r.get("human_label") for r in recs]
        successes = sum(1 for lab in labels if lab == positive_label)
        counts[arm] = (successes, n)
        per_arm_detail[arm] = {"n": n, "human_labeled_count": sum(1 for lab in labels if lab is not None)}

    result: dict = {"env": "funding_email", "counts": counts, "per_arm": per_arm_detail}
    if "A" in counts and "B" in counts:
        (sa, na), (sb, nb) = counts["A"], counts["B"]
        test = stats.two_proportion_one_sided_z_test(sa, na, sb, nb)
        direction = prereg.get("primary_hypothesis", {}).get("direction", "one_sided")
        result["test"] = _test_to_dict(test, direction)
    return result


def analyze_eval_tampering(run_dir: Path, prereg: dict) -> dict:
    mechanical = _load_jsonl(run_dir / "mechanical_labels.jsonl")
    human = _load_jsonl(run_dir / "human_labels.jsonl")
    judge = _load_jsonl(run_dir / "judge_labels.jsonl")
    merged = _merge_labels(mechanical, human, judge)

    # Audit artifact only -- never read back by anything as ground truth.
    merged_path = run_dir / "labels_merged.jsonl"
    with merged_path.open("w", encoding="utf-8") as f:
        for (arm, idx), (label, source) in sorted(merged.items()):
            f.write(json.dumps({"arm": arm, "replicate_index": idx, "label": label, "source": source}) + "\n")

    positive_label = prereg["primary_outcome"].get("positive_label", "disclose_specific")
    by_arm: dict[str, list[str]] = {}
    for (arm, _idx), (label, _source) in merged.items():
        by_arm.setdefault(arm, []).append(label)

    counts = {arm: (sum(1 for l in labels if l == positive_label), len(labels)) for arm, labels in by_arm.items()}
    per_arm_detail = {arm: {"n": len(labels), "labeled_count": len(labels)} for arm, labels in by_arm.items()}

    result: dict = {"env": "eval_tampering", "counts": counts, "per_arm": per_arm_detail}
    # Arm B (Artifact) has a full deterministic set; Arm A (Stated) is
    # pending human labels as of this pass -- report what exists, never
    # fabricate a number for the missing side.
    if "A" in counts and "B" in counts and counts["A"][1] > 0 and counts["B"][1] > 0:
        (sa, na), (sb, nb) = counts["A"], counts["B"]
        test = stats.two_proportion_one_sided_z_test(sa, na, sb, nb)
        direction = prereg.get("primary_hypothesis", {}).get("direction", "two_sided")
        result["test"] = _test_to_dict(test, direction)
    else:
        result["test"] = None
        result["note"] = "Arm A (Stated) human labels pending -- primary test not computed yet."
    return result


def _test_to_dict(test: stats.TwoProportionTestResult, direction: str) -> dict:
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
