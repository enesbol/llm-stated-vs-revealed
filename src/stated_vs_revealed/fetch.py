"""Fetch (or verify) files under envs/funding_email/vendor/, two-tier split.

  python -m stated_vs_revealed.fetch --verify           (default, no network)
  python -m stated_vs_revealed.fetch --fetch             (network, no API key)
  python -m stated_vs_revealed.fetch --fetch --samples   (also the 200 optional per-sample completions)

Core tier (MANIFEST.sha256): always committed, all the primary reproduction
needs. Samples tier (200 per-sample raw completions, 100/batch x 2 batches):
gitignored, NOT committed -- fetched on demand. Expected hashes for that
tier live in envs/funding_email/vendor/released_data/VERIFICATION.md (git
blob SHA-1, not sha256, since that's what HF/GitHub report), not in
MANIFEST.sha256. Ported from model-forensic-research/src/ours/fetch_and_verify.py
-- same two-tier discipline, same upstream sources, paths adjusted for this
repo's envs/<name>/vendor/ layout.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "envs" / "funding_email" / "vendor"
MANIFEST_PATH = REPO_ROOT / "MANIFEST.sha256"
SAMPLES_VERIFICATION_PATH = VENDOR_DIR / "released_data" / "VERIFICATION.md"

PAPER_REPO = "gkroiz/model_forensics_paper"
PAPER_COMMIT = "abb5fac45f19e91d8356b2f9cc63284cfd8f1bde"
BLOG_REPO = "gkroiz/investigating-model-motives-blog"
BLOG_COMMIT = "b36a8bc287e7d5c219d2bd50869397364a5ffb92"
HF_DATASET = "Model-Forensics/model-forensics"
HF_REVISION = "e9aa97a7aac835b56b67e28746429d57730b3bdb"

PAPER_FILES = {
    "src/model_incrimination_paper/api.py": "envs/funding_email/vendor/model_forensics_paper/api.py",
    "pyproject.toml": "envs/funding_email/vendor/model_forensics_paper/pyproject.toml",
}
BLOG_FILES = {
    "funding_email_details/PROMPT_TEMPLATES.md": "envs/funding_email/vendor/prompts/PROMPT_TEMPLATES.md",
    "funding_email_details/README.md": "envs/funding_email/vendor/prompts/funding_email_README.md",
    "funding_email_details/legal_review_variants/01_baseline.md": "envs/funding_email/vendor/prompts/legal_review_variants/01_baseline.md",
    "funding_email_details/workspace_files/cost_analysis.md": "envs/funding_email/vendor/prompts/workspace_files/cost_analysis.md",
    "funding_email_details/workspace_files/customer_feedback.md": "envs/funding_email/vendor/prompts/workspace_files/customer_feedback.md",
    "funding_email_details/workspace_files/field_trials_summary.md": "envs/funding_email/vendor/prompts/workspace_files/field_trials_summary.md",
    "funding_email_details/workspace_files/performance_benchmarks.md": "envs/funding_email/vendor/prompts/workspace_files/performance_benchmarks.md",
    "funding_email_details/workspace_files/technical_specifications.md": "envs/funding_email/vendor/prompts/workspace_files/technical_specifications.md",
    "funding_email_details/workspace_files/scheduled_emails/investor_email_draft.txt": "envs/funding_email/vendor/prompts/workspace_files/scheduled_emails/investor_email_draft.txt",
}
HF_BATCHES = ["2026-02-20_14-55-00", "2026-02-20_15-11-05"]
HF_CORE_NAMES = {"config.json", "grading_results.json"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest(manifest_path: Path = MANIFEST_PATH) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, relpath = line.partition("  ")
        entries[relpath] = digest
    return entries


def read_samples_verification(path: Path = SAMPLES_VERIFICATION_PATH) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `vendor/") or "/sample-" not in line:
            continue
        cols = [c.strip().strip("`") for c in line.strip("|").split("|")]
        local_path = cols[0].replace("vendor/", "envs/funding_email/vendor/", 1)
        oid = cols[1]
        entries[local_path] = oid
    return entries


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def verify_samples(root: Path = REPO_ROOT) -> tuple[int, int, list[str]]:
    if not SAMPLES_VERIFICATION_PATH.exists():
        return 0, 0, ["VERIFICATION.md missing -- cannot verify samples"]
    expected = read_samples_verification()
    ok = fail = present_count = 0
    problems: list[str] = []
    for local_path, want_oid in sorted(expected.items()):
        p = root / local_path
        if not p.exists():
            continue  # samples are optional; absence is not a failure here
        present_count += 1
        got = git_blob_sha1(p)
        if got != want_oid:
            fail += 1
            problems.append(f"MISMATCH {local_path} want={want_oid} got={got}")
        else:
            ok += 1
    if present_count == 0:
        problems.append(
            "No sample files found on disk. Run "
            "`python -m stated_vs_revealed.fetch --fetch --samples` to fetch them."
        )
    return ok, fail, problems


def _require_requests():
    try:
        import requests  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "The `requests` package is required for --fetch. `pip install -e .` "
            "or use the default --verify mode, which needs no network access."
        ) from e


def fetch(root: Path = REPO_ROOT, samples: bool = False) -> None:
    _require_requests()
    import requests

    session = requests.Session()

    def get(url: str, out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        out.write_bytes(resp.content)

    base = f"https://raw.githubusercontent.com/{PAPER_REPO}/{PAPER_COMMIT}"
    for upstream, local in PAPER_FILES.items():
        print(f"fetching {upstream}")
        get(f"{base}/{upstream}", root / local)

    base = f"https://raw.githubusercontent.com/{BLOG_REPO}/{BLOG_COMMIT}"
    for upstream, local in BLOG_FILES.items():
        print(f"fetching {upstream}")
        get(f"{base}/{upstream}", root / local)

    tree_url = (
        f"https://huggingface.co/api/datasets/{HF_DATASET}/tree/{HF_REVISION}/"
        "funding_email/ask_about_files?recursive=true"
    )
    resp = session.get(tree_url, timeout=30)
    resp.raise_for_status()
    tree = resp.json()
    hf_base = (
        f"https://huggingface.co/datasets/{HF_DATASET}/resolve/{HF_REVISION}/"
        "funding_email/ask_about_files"
    )
    for item in tree:
        if item["type"] != "file":
            continue
        rel = item["path"][len("funding_email/ask_about_files/"):]
        name = rel.split("/")[-1]
        if rel.split("/")[0] not in HF_BATCHES:
            continue
        if name in HF_CORE_NAMES:
            print(f"fetching {rel}")
            get(f"{hf_base}/{rel}", VENDOR_DIR / "released_data" / rel)
        elif samples and name == "result.json":
            print(f"fetching {rel}")
            get(f"{hf_base}/{rel}", VENDOR_DIR / "released_data" / rel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--samples", action="store_true", help="Also fetch/verify the 200 optional per-sample completions (gitignored)")
    args = parser.parse_args(argv)

    if args.fetch:
        fetch(samples=args.samples)

    from stated_vs_revealed.provenance import verify as verify_core

    ok, fail, problems = verify_core()
    print(f"core: {ok} ok, {fail} problems out of {ok + fail} manifest entries")
    for p in problems:
        print(" ", p)

    if args.samples:
        s_ok, s_fail, s_problems = verify_samples()
        print(f"\nsamples: {s_ok} ok, {s_fail} problems (of files present on disk)")
        for p in s_problems:
            print(" ", p)
        fail += s_fail

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
