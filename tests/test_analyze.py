"""Correctness bar for the ported analysis pipeline: the committed
Funding Email pilot data must reproduce the exact reported numbers
(29/30 Arm A vs 27/30 Arm B, one-sided p=0.150), and Eval Tampering's
pilot must reproduce 15/30 Arm A (Stated) vs 21/30 Arm B (Artifact),
diff -20.0pp."""

import json

from stated_vs_revealed import run
from stated_vs_revealed.analyze import analyze


def test_funding_email_pilot_reproduces_reported_counts():
    run_dir = run.REPO_ROOT / "results" / "live" / "funding_email" / "2026-08-12T16-44-24Z"
    prereg = json.loads((run.REPO_ROOT / "envs" / "funding_email" / "prereg" / "pilot.json").read_text(encoding="utf-8"))
    result = analyze("funding_email", run_dir, prereg)
    assert result["counts"]["A"] == (29, 30)
    assert result["counts"]["B"] == (27, 30)
    assert round(result["test"]["p_value_one_sided"], 3) == 0.150


def test_eval_tampering_artifact_arm_reproduces_deterministic_count():
    run_dir = run.REPO_ROOT / "results" / "live" / "eval_tampering" / "2026-09-04T19-28-19Z"
    prereg = json.loads(
        (run.REPO_ROOT / "envs" / "eval_tampering" / "prereg" / "eval_tampering.json").read_text(encoding="utf-8")
    )
    result = analyze("eval_tampering", run_dir, prereg)
    assert result["counts"]["A"] == (15, 30)
    assert result["counts"]["B"] == (21, 30)
    assert round(result["test"]["diff_pp"], 1) == -20.0
