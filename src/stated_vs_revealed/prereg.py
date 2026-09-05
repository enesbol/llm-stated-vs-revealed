"""Hash-lock a preregistration file: `python -m stated_vs_revealed.prereg <path>`.

Writes `<path>.sha256` (sibling file) containing the SHA-256 of the prereg
file's current bytes. run.py refuses to run unless this hash matches the
live prereg file, so this is what makes "preregistered" mean something more
than a filename. Ported unchanged (module-generic already) from
model-forensic-research/src/ours/lock_prereg.py.

Refuses to silently overwrite an existing lock. Use --force only with a
documented reason; the tool prints a loud warning either way.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lock(path: Path, force: bool = False) -> str:
    if not path.exists():
        raise FileNotFoundError(f"No such prereg file: {path}")
    digest = compute_sha256(path)
    lock_path = path.with_suffix(path.suffix + ".sha256")
    if lock_path.exists() and not force:
        existing = lock_path.read_text(encoding="utf-8").strip()
        if existing == digest:
            print(f"Already locked and unchanged: {lock_path}")
            return digest
        raise RuntimeError(
            f"{lock_path} already exists with a DIFFERENT hash than the current "
            f"{path.name}. The prereg file changed after it was locked. "
            "If this is an intentional pre-launch fix, re-run with --force and "
            "record why in the prereg's own change history -- never silently relock."
        )
    lock_path.write_text(digest + "\n", encoding="utf-8")
    print(f"Locked {path} -> {lock_path}\n  sha256={digest}")
    return digest


def verify(path: Path) -> bool:
    lock_path = path.with_suffix(path.suffix + ".sha256")
    if not lock_path.exists():
        return False
    if not path.exists():
        return False
    return lock_path.read_text(encoding="utf-8").strip() == compute_sha256(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to the preregistration JSON file")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing, different lock")
    parser.add_argument("--verify", action="store_true", help="Only verify, don't write")
    args = parser.parse_args(argv)

    if args.verify:
        ok = verify(args.path)
        print("LOCKED and MATCHES" if ok else "NOT LOCKED or MISMATCH")
        return 0 if ok else 1

    lock(args.path, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
