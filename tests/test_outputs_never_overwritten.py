"""Acceptance criterion: outputs are never overwritten. Ported from
model-forensic-research/tests/test_outputs_never_overwritten.py."""

import pytest


def test_results_dir_creation_fails_on_collision(tmp_path):
    d = tmp_path / "results" / "live" / "funding_email" / "2026-08-12T00-00-00Z"
    d.mkdir(parents=True, exist_ok=False)
    (d / "manifest.jsonl").write_text('{"already": "here"}\n', encoding="utf-8")

    with pytest.raises(FileExistsError):
        d.mkdir(parents=True, exist_ok=False)

    assert (d / "manifest.jsonl").read_text(encoding="utf-8") == '{"already": "here"}\n'


def test_run_uses_exist_ok_false_for_results_dir():
    import inspect

    from stated_vs_revealed import run

    src = inspect.getsource(run.main)
    assert "exist_ok=False" in src, "results_dir creation must refuse to reuse an existing directory"
