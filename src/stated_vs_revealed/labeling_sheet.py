"""Build a blinded, shuffled markdown labeling sheet from any env's
manifest.jsonl. Reads response text (and reasoning -- the reasoning-
blindness finding applies everywhere, the labeler needs both) but NOT the
arm, in a seeded-random order. A separate answer key (arm + replicate_index
per row) is written to a SEPARATE file so the labeler never sees it while
labeling. Ported from
model-forensic-research/src/ours/build_eval_tampering_labeling_sheet.py
(already environment-agnostic; only the label-set string is now a
parameter instead of hardcoded).

Usage:
    python -m stated_vs_revealed.labeling_sheet \\
        --manifest results/live/eval_tampering/<ts>/manifest.jsonl \\
        --label-set disclose_specific,conceal,ambiguous,refused,unaware \\
        --out docs/handoff/eval_tampering_labeling_sheet.md \\
        --key /tmp/eval_tampering_labeling_key.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def build(manifest_path: Path, out_path: Path, key_path: Path, label_set: str, seed: int = 20260904) -> None:
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    gradeable = [r for r in records if not r.get("excluded") and not r.get("error")]

    rng = random.Random(seed)
    order = list(range(len(gradeable)))
    rng.shuffle(order)

    lines = [
        "# Blinded labeling sheet\n",
        f"Arm is hidden. Label set: `{label_set}`.\n",
        "Paste a short supporting quote for every label. Do not open the key "
        "file until every row below is labeled.\n",
        "---\n",
    ]
    key = []
    for display_i, idx in enumerate(order, start=1):
        r = gradeable[idx]
        content = r.get("response_content") or "(empty)"
        reasoning = r.get("response_reasoning") or ""
        lines.append(f"## Row {display_i}\n")
        if reasoning:
            lines.append(f"**Reasoning:**\n\n```\n{reasoning}\n```\n")
        lines.append(f"**Response:**\n\n```\n{content}\n```\n")
        lines.append("**Label:** ____________  **Quote:** ____________\n")
        lines.append("---\n")
        key.append({"row": display_i, "arm": r["arm"], "replicate_index": r["replicate_index"]})

    out_path.write_text("\n".join(lines), encoding="utf-8")
    key_path.write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"Wrote {len(order)} blinded rows to {out_path}")
    print(f"Wrote answer key (arm mapping) to {key_path} -- do not open until labeling is done")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--label-set", required=True)
    parser.add_argument("--seed", type=int, default=20260904)
    args = parser.parse_args(argv)
    build(args.manifest, args.out, args.key, args.label_set, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
