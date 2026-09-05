"""Run any registered environment's pilot/main experiment.

    python -m stated_vs_revealed.run --config envs/funding_email/configs/pilot.json --dry-run
    python -m stated_vs_revealed.run --config envs/funding_email/configs/pilot.json

Config picks its env via the "env" key (a registry name from envs/__init__.py
ENVS), replacing the old prompt_module import-path mechanism. --dry-run makes
zero network calls: builds every prompt, proves prereg-lock + arm-diff
fidelity, prints the planned dispatch order, and exits.

Every real run writes to a fresh results/live/<env>/<UTC-timestamp>/
directory (never overwrites), enforces the config's usd_cap from OpenRouter's
own response.usage.cost (never a local token-count proxy), never sends an
inference seed, and excludes+flags any sample not served by the pinned
provider. Records are appended to the manifest the instant each completes
(not batched until the whole run finishes) -- a kill/crash mid-run loses at
most the in-flight calls, never everything already completed. Ported from
model-forensic-research/src/ours/run_experiment.py; see that repo's
CLAUDE.md for the incident this fix addresses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from stated_vs_revealed import check_duplicates
from stated_vs_revealed import prereg as prereg_mod
from stated_vs_revealed.envs import ENVS

REPO_ROOT = Path(__file__).resolve().parents[2]


class PreregNotLockedError(RuntimeError):
    pass


@dataclass
class Task:
    arm: str
    replicate_index: int


@dataclass
class SampleRecord:
    arm: str
    replicate_index: int
    request_messages: list[dict]
    request_model: str
    request_provider_preferences: dict
    request_temperature: float
    request_top_p: float
    request_max_tokens: int
    response_content: str | None = None
    response_reasoning: str | None = None
    response_finish_reason: str | None = None
    response_model: str | None = None
    response_provider: str | None = None
    usage_prompt_tokens: int | None = None
    usage_completion_tokens: int | None = None
    usage_cost_usd: float | None = None
    error: str | None = None
    excluded: bool = False
    exclusion_reason: str | None = None
    duration_seconds: float | None = None
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_env(config: dict):
    env_name = config["env"]
    if env_name not in ENVS:
        raise KeyError(f"Unknown env {env_name!r}. Registered: {sorted(ENVS)}")
    return ENVS[env_name]


def verify_prereg_locked(config: dict, root: Path = REPO_ROOT) -> None:
    prereg_file = root / config["prereg_file"]
    if not prereg_file.exists():
        raise PreregNotLockedError(f"{prereg_file} does not exist. A prereg must exist and be locked before any run.")
    if not prereg_mod.verify(prereg_file):
        raise PreregNotLockedError(
            f"{prereg_file} is not locked, or its contents don't match the recorded hash. Run "
            f"`python -m stated_vs_revealed.prereg {prereg_file}` and re-check nothing changed after locking."
        )


def build_task_order(config: dict) -> list[Task]:
    offset = config.get("replicate_offset", 0)
    tasks = [Task(arm=arm, replicate_index=offset + i) for arm in config["arms"] for i in range(config["n_per_arm"])]
    rng = random.Random(config["assignment_seed"])  # dispatch order only, never sent to the API
    rng.shuffle(tasks)
    return tasks


def normalize_provider_name(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def build_arm_prompts(config: dict) -> dict:
    env = get_env(config)
    diff_fn = getattr(env, "diff_arm_a_vs_b", None)
    if diff_fn is None:
        import importlib

        mod = importlib.import_module(type(env).__module__)
        diff_fn = mod.diff_arm_a_vs_b
    diff = diff_fn()
    if len(diff) != 1:
        raise RuntimeError(
            f"Arm A and Arm B must differ in exactly one line; found {len(diff)}. "
            "Refusing to run -- this is the design's core fidelity guarantee."
        )
    return {arm: env.build_prompt(arm) for arm in config["arms"]}


def dry_run(config: dict) -> int:
    verify_prereg_locked(config)
    arm_prompts = build_arm_prompts(config)
    task_order = build_task_order(config)

    print("DRY RUN -- zero network calls made.")
    print(f"env: {config['env']}  config: {config['run_name']}")
    print(f"prereg: {config['prereg_file']} -- LOCKED, matches current contents")
    print(f"model: {config['model']}  provider_preferences: {config['provider_preferences']}")
    print(f"n_per_arm: {config['n_per_arm']}  total tasks: {len(task_order)}")
    print(f"assignment_seed: {config['assignment_seed']} (dispatch order only, never sent to the API)")
    for arm, messages in arm_prompts.items():
        content = messages[-1]["content"]
        print(f"Arm {arm}: len={len(content)}  final ~120 chars: ...{content[-120:]!r}")
    print("First 10 dispatch-order tasks (post-shuffle):")
    for t in task_order[:10]:
        print(f"  arm={t.arm} replicate_index={t.replicate_index}")
    print(f"usd_cap: ${config['usd_cap']:.2f}")
    print("No pre-flight cost estimate -- the cap is enforced live from OpenRouter's own response.usage.cost.")
    return 0


async def _run_live(config: dict, results_dir: Path) -> list[SampleRecord]:
    from tqdm import tqdm

    from stated_vs_revealed._vendor_api import load as load_vendor_api

    vendor_api = load_vendor_api()
    client = vendor_api.get_openrouter_client()

    env = get_env(config)
    arm_prompts = build_arm_prompts(config)
    task_order = build_task_order(config)

    spend_lock = asyncio.Lock()
    spend_state = {"usd": 0.0}
    semaphore = asyncio.Semaphore(config["max_concurrent"])
    allowed_provider = set(config["provider_preferences"].get("only", []))

    manifest_path = results_dir / "manifest.jsonl"
    manifest_file = manifest_path.open("a", encoding="utf-8")
    write_lock = asyncio.Lock()

    async def append_record(record: SampleRecord) -> None:
        async with write_lock:
            manifest_file.write(json.dumps(asdict(record)) + "\n")
            manifest_file.flush()

    async def run_one(task: Task) -> SampleRecord:
        record = await _run_one_inner(task)
        await append_record(record)
        return record

    async def _run_one_inner(task: Task) -> SampleRecord:
        messages = arm_prompts[task.arm]
        record = SampleRecord(
            arm=task.arm,
            replicate_index=task.replicate_index,
            request_messages=messages,
            request_model=config["model"],
            request_provider_preferences=config["provider_preferences"],
            request_temperature=config["temperature"],
            request_top_p=config["top_p"],
            request_max_tokens=config["max_tokens"],
        )
        async with spend_lock:
            if spend_state["usd"] >= config["usd_cap"]:
                record.error = "cost_cap_reached_before_dispatch"
                return record
        async with semaphore:
            # Timer starts here, after the semaphore gate, so duration_seconds
            # measures real API call latency -- not time queued behind other
            # concurrent calls (that bug made later records in a long run
            # report a climbing, meaningless "duration" of thousands of
            # seconds; see docs/findings.md 2026-09-05).
            start = time.monotonic()
            try:
                response = await vendor_api.call_api(
                    client=client,
                    model=config["model"],
                    messages=messages,
                    temperature=config["temperature"],
                    top_p=config["top_p"],
                    max_tokens=config["max_tokens"],
                    extra_body={"provider": config["provider_preferences"], "usage": {"include": True}},
                    # NEVER pass seed=... here.
                )
            except Exception as e:  # noqa: BLE001 - record and continue, don't crash the batch
                record.error = f"{type(e).__name__}: {e}"
                record.duration_seconds = time.monotonic() - start
                return record
            record.duration_seconds = time.monotonic() - start

        choice = response.choices[0]
        record.response_content = choice.message.content
        record.response_reasoning = getattr(choice.message, "reasoning", None)
        record.response_finish_reason = choice.finish_reason
        record.response_model = response.model
        served_provider = getattr(response, "provider", None) or (getattr(response, "model_extra", {}) or {}).get("provider")
        record.response_provider = served_provider
        if allowed_provider and normalize_provider_name(served_provider) not in {
            normalize_provider_name(p) for p in allowed_provider
        }:
            record.excluded = True
            record.exclusion_reason = f"served_provider={served_provider!r} not in {allowed_provider!r}"

        if response.usage is not None:
            record.usage_prompt_tokens = response.usage.prompt_tokens
            record.usage_completion_tokens = response.usage.completion_tokens
            cost = getattr(response.usage, "cost", None)
            if cost is None:
                raise RuntimeError("response.usage.cost missing -- refusing to fall back to a local token estimate.")
            record.usage_cost_usd = cost
            async with spend_lock:
                spend_state["usd"] += cost
        return record

    records: list[SampleRecord] = []
    pbar = tqdm(total=len(task_order), desc=f"{config['run_name']} generation", unit="call")
    for coro in asyncio.as_completed([run_one(t) for t in task_order]):
        record = await coro
        records.append(record)
        elapsed = f"{record.duration_seconds:.1f}s" if record.duration_seconds is not None else "?"
        pbar.set_postfix_str(f"last={elapsed} spend=${spend_state['usd']:.4f}")
        pbar.update(1)
    pbar.close()

    durations = [r.duration_seconds for r in records if r.duration_seconds is not None]
    if durations:
        ideal_parallel_seconds = sum(durations) / config["max_concurrent"]
        print(f"Per-call duration: mean={sum(durations)/len(durations):.1f}s min={min(durations):.1f}s max={max(durations):.1f}s")
        print(f"Ideal fully-packed parallel time at concurrency {config['max_concurrent']}: {ideal_parallel_seconds:.1f}s")

    next_replicate_offset = 1_000_000
    for _resample_pass in range(config.get("duplicate_resample_limit", 1)):
        by_arm_texts: dict[str, list[tuple[int, str]]] = {}
        for i, r in enumerate(records):
            if r.response_content and not r.excluded and not r.error:
                by_arm_texts.setdefault(r.arm, []).append((i, r.response_content))

        resample_tasks: list[tuple[int, Task]] = []
        for arm, indexed_texts in by_arm_texts.items():
            texts = [t for _, t in indexed_texts]
            rep = check_duplicates.detect(arm, texts)
            for local_idx in rep.normalized_duplicate_indices:
                record_idx, _ = indexed_texts[local_idx]
                records[record_idx].excluded = True
                records[record_idx].exclusion_reason = "duplicate_resampled"
                resample_tasks.append((record_idx, Task(arm=arm, replicate_index=next_replicate_offset)))
                next_replicate_offset += 1

        if not resample_tasks:
            break
        new_records = await asyncio.gather(*(run_one(t) for _, t in resample_tasks))
        records.extend(new_records)

    manifest_file.close()
    with manifest_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + "\n")
    print(f"Wrote {len(records)} records to {manifest_path}")
    print(f"Cumulative actual spend: ${spend_state['usd']:.4f} of ${config['usd_cap']:.2f} cap")

    ledger_path = results_dir / "spend_ledger.json"
    ledger_path.write_text(
        json.dumps({"generation_usd": spend_state["usd"], "usd_cap": config["usd_cap"]}, indent=2), encoding="utf-8"
    )
    return records


def check_duplicates_and_report(records: list[SampleRecord], config: dict, results_dir: Path) -> None:
    by_arm: dict[str, list[str]] = {}
    for r in records:
        if r.response_content and not r.excluded and not r.error:
            by_arm.setdefault(r.arm, []).append(r.response_content)

    report_lines = ["# Duplicate report\n"]
    for arm, texts in by_arm.items():
        rep = check_duplicates.detect(arm, texts)
        over = check_duplicates.over_threshold(rep, config["duplicate_kill_threshold_frac"])
        report_lines.append(
            f"Arm {arm}: n={rep.n} normalized_duplicates={len(rep.normalized_duplicate_indices)} "
            f"rate={rep.duplicate_rate:.3f} kill_threshold={config['duplicate_kill_threshold_frac']} "
            f"{'OVER THRESHOLD' if over else 'ok'}"
        )
    (results_dir / "duplicate_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print("\n".join(report_lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)

    if args.dry_run:
        return dry_run(config)

    verify_prereg_locked(config)
    build_arm_prompts(config)  # raises on any fidelity/diff problem before touching the network

    results_dir = REPO_ROOT / "results" / "live" / config["env"] / time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    results_dir.mkdir(parents=True, exist_ok=False)  # never overwrite a prior run
    (results_dir / "config_used.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    records = asyncio.run(_run_live(config, results_dir))
    check_duplicates_and_report(records, config, results_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
