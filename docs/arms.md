# The S / A / T framework — what these letters mean

This project tests one mechanism across multiple environments: **does making
a model commit to a concrete output change its behavior, compared to just
asking what it would do?** Three conditions, not always all three:

- **S — Stated action.** "What would you do?" The model describes its
  intended action in prose. No artifact is produced, nothing is executed.
  This is what the Funding Email / Eval Tampering code in this repo calls
  **Arm A**, same condition, different name. S is short for "stated."
- **A — Artifact.** "Write the exact [email / submit payload] you would
  send." The model must produce the literal, final, concrete thing — but
  still doesn't send/submit/execute it. This is what earlier code calls
  **Arm B**. A is short for "artifact."
- **T — Tool-call / action-schema commitment.** The model emits a
  structured, machine-parseable action format (e.g. Anthropic's
  `<tool_use:email>...</tool_use:email>` XML) **inside its own final chat
  response**. This is the closest thing to "acting" that a single-turn,
  no-tool-execution setup can produce — but it is still not executed
  action. No email actually sends, no file actually changes. **This
  distinction matters and is easy to get wrong**: Anthropic's own published
  blackmail/leaking rates come from exactly this T-style single-response
  setup, not from a real multi-turn agentic rollout with actual tool
  execution. Citing T as "the model acted" overstates what happened.

## Why the two environments in this repo only have S/A

Both Funding Email and Eval Tampering's released source material is
S-shaped (a single free-form question); neither released a T condition
(tool-schema-in-final-response), and neither was reconstructed here. A
third environment with a real T arm (Blackmail) is planned but not built,
see `docs/next.md`.

**Grading principle that generalizes across arms:** an automated classifier
built to parse structured action syntax (tool calls, schema fields) cannot
score a free-form S or A response fairly, since those arms are explicitly
told to describe or draft, not to emit that syntax. Primary grading must be
human labels reading the model's stated intent semantically, with any
automated judge validated against those human labels per arm before being
trusted, the same lesson this project learned twice already (Funding
Email's reasoning-blindness judge bug, Eval Tampering's rubric-scope
mismatch).
