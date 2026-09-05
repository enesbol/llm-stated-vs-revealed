"""Verify every vendored file under envs/*/vendor/ against MANIFEST.sha256.

    python -m stated_vs_revealed.provenance --verify
    python -m stated_vs_revealed.provenance --generate   # regenerate after adding a vendored file

This is a generic, path-relative checker over whatever `envs/*/vendor/`
actually contains -- it doesn't re-fetch from Hugging Face/GitHub itself
(that live-fetch machinery, model-forensic-research/src/ours/fetch_and_verify.py,
is not ported here yet; every vendored file already needed for the two
built environments is committed directly). See PROVENANCE.md and each
envs/<name>/vendor/README.md for exact upstream source/revision.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "MANIFEST.sha256"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vendored_files(root: Path = REPO_ROOT) -> list[Path]:
    """Git-tracked files only, via `git ls-files` -- never a disk glob.
    A glob over envs/*/vendor/**/* previously picked up 200 untracked,
    gitignored sample-*/result.json files that happened to be sitting on
    disk locally (fetched for convenience, never committed), breaking
    verification on any fresh clone that lacks them. `git ls-files` reflects
    exactly what's committed, which is the only thing MANIFEST.sha256 can
    ever promise to verify."""
    out = subprocess.run(
        ["git", "ls-files", "envs/"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    return sorted(
        root / line for line in out.splitlines() if line.strip() and "/vendor/" in line
    )


def generate(root: Path = REPO_ROOT) -> None:
    lines = []
    for path in vendored_files(root):
        if path.is_file() and "__pycache__" not in path.parts:
            rel = path.relative_to(root)
            lines.append(f"{_sha256_file(path)}  {rel}")
    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} entries to {MANIFEST_PATH}")


def verify(root: Path = REPO_ROOT) -> tuple[int, int, list[str]]:
    if not MANIFEST_PATH.exists():
        return (0, 0, [f"{MANIFEST_PATH} does not exist -- run --generate first"])
    ok = 0
    fail = 0
    problems: list[str] = []
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        path = root / rel
        if not path.exists():
            fail += 1
            problems.append(f"MISSING {rel}")
            continue
        actual = _sha256_file(path)
        if actual == digest:
            ok += 1
        else:
            fail += 1
            problems.append(f"MISMATCH {rel}: expected {digest}, got {actual}")
    return ok, fail, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args(argv)

    if args.generate:
        generate()
        return 0
    if args.verify:
        ok, fail, problems = verify()
        print(f"{ok} OK, {fail} FAILED")
        for p in problems:
            print(f"  {p}")
        return 0 if fail == 0 else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
