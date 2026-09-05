"""Acceptance criteria: Arm A is byte-identical (SHA-256) to the vendored
anchor prompt; Arm A and Arm B differ in exactly one line. Ported from
model-forensic-research/tests/test_prompt_diff.py."""

import hashlib
import json

from stated_vs_revealed.envs import funding_email as fe


def test_arm_a_byte_identical_to_vendored_anchor():
    anchor = json.loads(fe.DEFAULT_ANCHOR_PATH.read_text(encoding="utf-8"))
    anchor_content = anchor["messages"][0]["content"]
    arm_a = fe.build_arm_a()
    assert arm_a.content == anchor_content
    assert arm_a.sha256 == hashlib.sha256(anchor_content.encode("utf-8")).hexdigest()


def test_arm_a_and_arm_b_differ_in_exactly_one_line():
    diff = fe.diff_arm_a_vs_b()
    assert len(diff) == 1, f"expected exactly 1 differing line, found {len(diff)}: {diff}"
    _, line_a, line_b = diff[0]
    assert line_a == fe.ARM_A_FINAL_LINE
    assert line_b == fe.ARM_B_FINAL_LINE


def test_arm_b_is_not_equal_to_arm_a():
    a = fe.build_arm_a()
    b = fe.build_arm_b()
    assert a.content != b.content
    assert a.sha256 != b.sha256


def test_verify_arm_a_fidelity_passes_on_untouched_vendor_data():
    sha = fe.verify_arm_a_fidelity()
    assert sha == fe.build_arm_a().sha256


def test_verify_arm_a_fidelity_raises_on_tampered_anchor(tmp_path):
    tampered = tmp_path / "config.json"
    original = json.loads(fe.DEFAULT_ANCHOR_PATH.read_text(encoding="utf-8"))
    original["messages"][0]["content"] = original["messages"][0]["content"].replace(
        "What would you do?", "What would you do?!"
    )
    tampered.write_text(json.dumps(original), encoding="utf-8")
    try:
        fe.verify_arm_a_fidelity(tampered)
        assert False, "expected AnchorMismatchError on a tampered anchor file"
    except fe.AnchorMismatchError:
        pass
