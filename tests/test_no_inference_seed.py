"""Acceptance criterion: no inference seed is ever transmitted to the model.
Exercises the real live-call code path (_run_live) against a fake vendor API
module. Ported from model-forensic-research/tests/test_no_inference_seed.py."""

import asyncio
import json
import types

import pytest

from stated_vs_revealed import run


class _FakeUsage:
    def __init__(self, p=100, c=50):
        self.prompt_tokens = p
        self.completion_tokens = c
        self.cost = 0.0001


class _FakeMessage:
    def __init__(self, content="ok"):
        self.content = content
        self.reasoning = None


class _FakeChoice:
    def __init__(self):
        self.message = _FakeMessage()
        self.finish_reason = "stop"


class _FakeResponse:
    def __init__(self):
        self.choices = [_FakeChoice()]
        self.model = "moonshotai/kimi-k2.5"
        self.usage = _FakeUsage()
        self.provider = "moonshotai"


@pytest.fixture()
def fake_vendor_api(monkeypatch):
    captured_calls = []

    async def fake_call_api(client, model, messages, **kwargs):
        captured_calls.append({"model": model, "messages": messages, **kwargs})
        return _FakeResponse()

    def fake_get_client():
        return object()

    fake_module = types.SimpleNamespace(get_openrouter_client=fake_get_client, call_api=fake_call_api)

    from stated_vs_revealed import _vendor_api

    monkeypatch.setattr(_vendor_api, "load", lambda: fake_module)
    return captured_calls


@pytest.fixture()
def tiny_config():
    config = json.loads((run.REPO_ROOT / "envs" / "funding_email" / "configs" / "pilot.json").read_text(encoding="utf-8"))
    config["n_per_arm"] = 1  # 2 total tasks, fast test
    return config


def test_no_seed_kwarg_ever_sent(fake_vendor_api, tiny_config, tmp_path):
    results_dir = tmp_path / "run"
    results_dir.mkdir()
    asyncio.run(run._run_live(tiny_config, results_dir))

    assert len(fake_vendor_api) == 2  # one per arm
    for call in fake_vendor_api:
        assert "seed" not in call, f"inference call included a seed kwarg: {call}"


def test_manifest_written_with_no_seed_field(fake_vendor_api, tiny_config, tmp_path):
    results_dir = tmp_path / "run"
    results_dir.mkdir()
    asyncio.run(run._run_live(tiny_config, results_dir))

    manifest = results_dir / "manifest.jsonl"
    assert manifest.exists()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        assert "seed" not in record
        assert record["response_provider"] == "moonshotai"
        assert not record["excluded"]
