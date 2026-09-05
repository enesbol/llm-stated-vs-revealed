"""Acceptance criterion: the prereg is provably pre-inference. Missing or
mismatched lock files must refuse the run, not warn and continue. Ported
from model-forensic-research/tests/test_prereg_lock.py, paths updated for
the envs/<name>/prereg/ layout."""

import json

import pytest

from stated_vs_revealed import prereg as prereg_mod
from stated_vs_revealed import run


def test_funding_email_pilot_prereg_is_locked_in_repo():
    assert prereg_mod.verify(run.REPO_ROOT / "envs" / "funding_email" / "prereg" / "pilot.json")


def test_eval_tampering_prereg_is_locked_in_repo():
    assert prereg_mod.verify(run.REPO_ROOT / "envs" / "eval_tampering" / "prereg" / "eval_tampering.json")


def test_verify_prereg_locked_passes_for_real_pilot_config():
    config = run.load_config(run.REPO_ROOT / "envs" / "funding_email" / "configs" / "pilot.json")
    run.verify_prereg_locked(config)  # must not raise


def test_verify_prereg_locked_raises_when_prereg_missing(tmp_path):
    config = {"prereg_file": "envs/funding_email/prereg/does_not_exist.json"}
    with pytest.raises(run.PreregNotLockedError):
        run.verify_prereg_locked(config, root=tmp_path)


def test_verify_prereg_locked_raises_when_hash_stale(tmp_path):
    prereg_dir = tmp_path / "envs" / "funding_email" / "prereg"
    prereg_dir.mkdir(parents=True)
    prereg_path = prereg_dir / "pilot.json"
    prereg_path.write_text(json.dumps({"claim": "v1"}), encoding="utf-8")
    prereg_mod.lock(prereg_path)

    prereg_path.write_text(json.dumps({"claim": "v2 - edited after lock"}), encoding="utf-8")

    config = {"prereg_file": "envs/funding_email/prereg/pilot.json"}
    with pytest.raises(run.PreregNotLockedError):
        run.verify_prereg_locked(config, root=tmp_path)


def test_lock_refuses_silent_relock_on_changed_file(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    prereg_mod.lock(p)
    p.write_text(json.dumps({"a": 2}), encoding="utf-8")
    with pytest.raises(RuntimeError):
        prereg_mod.lock(p)  # no --force -> must refuse
    prereg_mod.lock(p, force=True)
    assert prereg_mod.verify(p)
