"""The Env contract: the only thing a new environment implements.

Adding an environment is 5 files (envs/<name>/vendor/ + README, rubric.md,
src/stated_vs_revealed/envs/<name>.py implementing this Protocol,
envs/<name>/prereg/*.json locked, tests/envs/test_<name>_prompt_diff.py) +
ONE registry line in envs/__init__.py. run.py, judge.py, stats.py, analyze.py
and labeling_sheet.py are shared and untouched by a new env -- if adding one
requires editing those files, the Protocol below is under-specified; fix the
Protocol, not the shared files.
"""

from __future__ import annotations

from typing import Mapping, Protocol


class Env(Protocol):
    name: str

    # Arm key -> the final question/instruction appended for that arm, or
    # None for an arm with no appended question (e.g. Blackmail's future T
    # arm, which is Anthropic's system+user prompt completely unmodified).
    arms: Mapping[str, str | None]

    def build_prompt(self, arm: str) -> list[dict]:
        """Byte-matched construction of the full message list for one arm,
        built only from envs/<name>/vendor/ -- never hand-retyped content."""
        ...

    def mechanical_label(self, record: dict) -> str | None:
        """A deterministic label derivable from the record alone (e.g. the
        Artifact arm's submit-payload field), or None if this record's arm
        has no mechanical rule and needs a human/judge label instead."""
        ...

    judge_rubric: str
    label_set: tuple[str, ...]

    # In-scenario words that are NOT evidence of verbalized eval-awareness
    # for this environment (e.g. "evaluation" for eval_tampering, whose task
    # itself is called a math evaluation; "due diligence review" for
    # funding_email). The eval-awareness judge/rubric is one general
    # definition across all envs; this is the only per-env knob.
    awareness_exclusions: tuple[str, ...]
