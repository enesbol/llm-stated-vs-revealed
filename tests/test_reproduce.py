"""run_tests() must warn and continue when pytest itself isn't installed,
never silently report that as a failing suite -- those are different
problems (missing dependency vs. a real red test) with different fixes.

regenerate_summary() must never silently drop a run whose config_used.json
points at a prereg file that doesn't exist -- it becomes a recorded error,
which main() then turns into a non-zero exit."""

import json

from stated_vs_revealed import reproduce


def test_run_tests_warns_and_continues_when_pytest_missing(monkeypatch, capsys):
    monkeypatch.setattr(reproduce.importlib.util, "find_spec", lambda name: None)
    ok = reproduce.run_tests()
    assert ok is True
    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "pytest is not installed" in out


def test_missing_prereg_file_becomes_an_error_not_a_silent_skip(tmp_path, monkeypatch):
    fake_root = tmp_path
    run_dir = fake_root / "results" / "live" / "funding_email" / "2099-01-01T00-00-00Z"
    run_dir.mkdir(parents=True)
    (run_dir / "config_used.json").write_text(json.dumps({"prereg_file": "envs/funding_email/prereg/does_not_exist.json"}))
    monkeypatch.setattr(reproduce, "REPO_ROOT", fake_root)
    monkeypatch.setattr(reproduce, "ENVS", {"funding_email": object()})

    summary = reproduce.regenerate_summary()
    runs = summary["funding_email"]
    assert len(runs) == 1
    assert "error" in runs[0]
    assert "does_not_exist.json" in runs[0]["error"]
