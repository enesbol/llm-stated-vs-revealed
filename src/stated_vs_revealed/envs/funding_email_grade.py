"""Grade a Funding Email run with the judge-per-arm rule (docs/labeling.md,
docs/findings.md 2026-09-05 calibration table): Arm B (Artifact) -> agentic
rubric on google/gemini-3.1-pro-preview; Arm A (Stated) -> third-person
rubric on google/gemini-3.8-flash. Writes judge_labels.jsonl into the run
directory (never mechanical_labels.jsonl -- Funding Email has no
deterministic rule) and continues spend from the run's own
spend_ledger.json (pooled generation+grading budget, CLAUDE.md rule 10
equivalent).

Usage:
    python -m stated_vs_revealed.envs.funding_email_grade --run results/live/funding_email/<ts>
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import openai

from stated_vs_revealed._vendor_api import load as load_vendor_api
from stated_vs_revealed.envs.funding_email_judges import (
    AGENTIC_JUDGE_MODEL,
    AGENTIC_JUDGE_PROVIDER,
    ARM_A_FINAL_LINE,
    THIRD_PERSON_JUDGE_MODEL,
    format_agentic_judge_messages,
    format_third_person_judge_messages,
    load_scenario_materials,
)


def _read_manifest(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_judge_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
    return json.loads(text.strip())


def _judge_input(record: dict) -> str:
    content = record.get("response_content") or ""
    reasoning = record.get("response_reasoning") or ""
    if reasoning:
        return f"<reasoning>\n{reasoning}\n</reasoning>\n\n<final_response>\n{content}\n</final_response>"
    return content


async def grade(records: list[dict], usd_cap: float, starting_spend: float, max_concurrent: int) -> tuple[list[dict], float]:
    vendor_api = load_vendor_api()
    client = vendor_api.get_openrouter_client()
    materials = load_scenario_materials()
    semaphore = asyncio.Semaphore(max_concurrent)
    spend = {"usd": starting_spend}

    async def call_judge(messages: list[dict], model: str, provider: dict | None) -> dict:
        if spend["usd"] >= usd_cap:
            return {"error": "cost_cap_reached"}
        extra_body = {"usage": {"include": True}}
        if provider is not None:
            extra_body["provider"] = provider
        for attempt in range(3):
            try:
                async with semaphore:
                    response = await vendor_api.call_api(
                        client=client, model=model, messages=messages,
                        temperature=0.0, max_tokens=8000, extra_body=extra_body,
                    )
                break
            except openai.APIStatusError as e:
                if e.status_code == 402 and attempt < 2:
                    retry_after = float(e.response.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    continue
                return {"error": f"api_error: {e.status_code} {e.message}"}
        if response.usage is not None:
            cost = getattr(response.usage, "cost", None)
            if cost is None:
                raise RuntimeError("response.usage.cost missing -- refusing local token estimate.")
            spend["usd"] += cost
        try:
            return _parse_judge_json(response.choices[0].message.content)
        except (json.JSONDecodeError, IndexError) as e:
            return {"error": f"parse_failed: {e}", "raw": response.choices[0].message.content}

    async def grade_one(record: dict) -> dict:
        graded = dict(record)
        if record.get("excluded") or record.get("error"):
            graded["judge"] = None
            return graded
        judge_input = _judge_input(record)
        if not judge_input:
            graded["judge"] = None
            return graded
        if record["arm"] == "B":  # Artifact -> agentic rubric, gemini-3.1-pro
            messages = format_agentic_judge_messages(judge_input, materials)
            graded["judge"] = await call_judge(messages, AGENTIC_JUDGE_MODEL, AGENTIC_JUDGE_PROVIDER)
            graded["judge_role"] = "agentic"
        else:  # Stated -> third-person rubric, cheap gemini-3.8-flash
            question = ARM_A_FINAL_LINE
            messages = format_third_person_judge_messages(judge_input, question, materials)
            graded["judge"] = await call_judge(messages, THIRD_PERSON_JUDGE_MODEL, None)
            graded["judge_role"] = "third_person"
        return graded

    graded = list(await asyncio.gather(*(grade_one(r) for r in records)))
    return graded, spend["usd"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--usd-cap", type=float, default=7.0)
    parser.add_argument("--max-concurrent", type=int, default=6)
    args = parser.parse_args(argv)

    records = _read_manifest(args.run / "manifest.jsonl")
    ledger_path = args.run / "spend_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    starting_spend = ledger.get("combined_usd", ledger.get("generation_usd", 0.0))

    graded: list[dict] = []
    final_spend = starting_spend
    try:
        graded, final_spend = asyncio.run(grade(records, args.usd_cap, starting_spend, args.max_concurrent))
    finally:
        out_path = args.run / "judge_labels.jsonl"
        rows = []
        for g in graded:
            j = g.get("judge") or {}
            if not j or j.get("error"):
                continue
            label = j.get("disclosure_level") if g.get("judge_role") == "agentic" else j.get("stated_action")
            # Map both judges' label sets onto the shared 5-way funding-email set.
            LABEL_MAP = {"none": "no_disclosure", "vague": "disclose_vague", "specific": "disclose_specific"}
            label = LABEL_MAP.get(label, label)
            rows.append({
                "arm": g["arm"], "replicate_index": g["replicate_index"], "label": label,
                "judge_role": g.get("judge_role"), "raw_judge": j,
            })
        with out_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        ledger_path.write_text(
            json.dumps({"generation_usd": ledger.get("generation_usd", starting_spend), "combined_usd": final_spend, "usd_cap": args.usd_cap}, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {len(rows)}/{len(records)} judge labels to {out_path}")
        print(f"Cumulative spend (generation + judge): ${final_spend:.4f} of ${args.usd_cap:.2f} cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
