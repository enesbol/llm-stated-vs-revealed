"""Export every tracked repo file into one context.md.

Usage: python context.py [output_path]   (default: context.md)

Lists files via `git ls-files` (respects .gitignore and what's actually
committed, not a manual walk), skips binaries and a short excludes list of
files that are noise for a human/LLM reading the repo (large hash
manifests, generated lockfiles), and renders everything else as a fenced
code block under its path.
"""
from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# This dump is for an LLM reading the codebase: source, tests, docs,
# small configs. Not raw run data, not generated label sheets, not hash
# manifests -- those are real and necessary to the project, just not
# useful as *context* to read. Extend this list rather than the code below.
EXCLUDE_PATHS = {
    "MANIFEST.sha256",
    "context.py",
}
EXCLUDE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".lock"}
EXCLUDE_DIR_PARTS = {"__pycache__", ".git"}
# Vendored upstream data blobs (released_data/config.json carries the full
# anchor prompt text) are skipped by directory segment. results/live/ is
# NOT excluded wholesale -- a reviewer needs the small per-run label files
# (human_labels.jsonl, mechanical_labels.jsonl, consultative_labels.jsonl,
# config_used.json, duplicate_report.md, spend_ledger.json) to verify
# numbers. Only the raw-transcript files are excluded, by filename, below.
EXCLUDE_DIR_SEGMENTS = {"released_data"}
# Raw per-run generation/grading blobs: full request/response transcripts
# (manifest.jsonl, graded*.jsonl) or raw judge output (judge_labels.jsonl).
# Matched by filename anywhere in the tree, not just under results/live/.
EXCLUDE_FILENAME_GLOBS = {"manifest.jsonl", "graded*.jsonl", "judge_labels.jsonl"}
# A file this long is a generated artifact (a labeling sheet, a big JSON
# dump), not something to read line by line -- skip it with a note instead
# of silently blowing up the dump again like the 50k-line labeling sheet did.
MAX_LINES = 2000

LANG_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
    ".sh": "bash",
    ".toml": "toml",
    ".txt": "text",
    ".sha256": "text",
    ".gitignore": "text",
}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    paths = [ROOT / line for line in out.splitlines() if line.strip()]
    kept = []
    for p in paths:
        rel = p.relative_to(ROOT)
        if str(rel) in EXCLUDE_PATHS:
            continue
        if p.suffix in EXCLUDE_SUFFIXES:
            continue
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        if EXCLUDE_DIR_SEGMENTS & set(rel.parts):
            continue
        if any(fnmatch.fnmatch(p.name, pat) for pat in EXCLUDE_FILENAME_GLOBS):
            continue
        kept.append(p)
    return sorted(kept)


def lang_for(path: Path) -> str:
    return LANG_BY_SUFFIX.get(path.suffix, "")


def render(paths: list[Path]) -> str:
    lines = [f"# Repository context: {ROOT.name}", "", f"{len(paths)} files.", ""]
    for p in paths:
        rel = p.relative_to(ROOT)
        lines.append(f"## `{rel}`")
        lines.append("")
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            lines.append(f"*(binary or non-UTF-8 file, {p.stat().st_size} bytes, skipped)*")
            lines.append("")
            continue
        n_lines = text.count("\n") + 1
        if n_lines > MAX_LINES:
            lines.append(f"*({n_lines} lines, over the {MAX_LINES}-line context cap, skipped)*")
            lines.append("")
            continue
        fence = "````" if "```" in text else "```"
        lines.append(f"{fence}{lang_for(p)}")
        lines.append(text.rstrip("\n"))
        lines.append(fence)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    out_path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "context.md")
    paths = tracked_files()
    out_path.write_text(render(paths), encoding="utf-8")
    print(f"Wrote {out_path} from {len(paths)} files.")


if __name__ == "__main__":
    main()
