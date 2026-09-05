"""Acceptance criterion: dry run makes zero API calls. Ported from
model-forensic-research/tests/test_dry_run_no_network.py."""

import pytest

from stated_vs_revealed import run


@pytest.fixture()
def pilot_config():
    return run.load_config(run.REPO_ROOT / "envs" / "funding_email" / "configs" / "pilot.json")


def test_dry_run_never_constructs_a_client(pilot_config, monkeypatch, capsys):
    def _boom(*_a, **_kw):
        raise AssertionError("dry-run must never construct an API client")

    from stated_vs_revealed import _vendor_api

    monkeypatch.setattr(_vendor_api, "load", _boom)

    rc = run.dry_run(pilot_config)
    assert rc == 0

    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "zero network calls" in out


def test_dry_run_does_not_import_openai_client_module(pilot_config):
    import inspect

    src = inspect.getsource(run.dry_run)
    assert "asyncio" not in src
    assert "_vendor_api" not in src
    assert "get_openrouter_client" not in src
