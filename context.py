"""Export every tracked repo file into one context.md.

Usage: python context.py [output_path]   (default: context.md)

Lists files via `git ls-files` (respects .gitignore and what's actually
committed, not a manual walk), skips binaries and a short excludes list of
files that are noise for a human/LLM reading the repo (large hash
manifests, generated lockfiles), and renders everything else as a fenced
code block under its path.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Files that are real, necessary, and tracked, but add no value to a
# read-through context dump (regenerable, or just noise: hash lists,
# binary images, lockfiles). Extend this list rather than the code below.
EXCLUDE_PATHS = {
    "MANIFEST.sha256",
    "context.py",
}
EXCLUDE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".lock"}
EXCLUDE_DIR_PARTS = {"__pycache__", ".git"}

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
