# Next — deliberately not built here yet

## Blackmail (S/A/T)

The first environment with a real third arm: Anthropic's own released
system prompt for the Blackmail scenario already wires in `<tool_use:email>`
instructions, so a Tool-call (T) arm is Anthropic's real, unmodified setup
rather than something invented for this repo. Prompts are already vendored
in the working repo (not yet ported here) via
`anthropic-experimental/agentic-misalignment`'s own `scripts/generate_prompts.py`,
run locally for byte-faithful output. Structural note: Anthropic's own
harmful-behavior classifier requires `<tool_use:...>` tags to score, so it
cannot grade S/A fairly — human labeling is the only usable primary
instrument there too.

## A real executed-action (X) arm

Everything in this repo so far is single-turn, no-tool-execution — even the
"Artifact"/"Tool call" arms are still a model producing text, never a real
side effect. An `X` arm needs an actual multi-turn agentic rollout with real
tool execution (the paper's own agentic setup, or `gkroiz/agent-interp-envs`
directly). This is real, separate infrastructure work — a tool/executor
interface is deliberately NOT built into the current `Env` protocol; don't
add one speculatively before X is actually being built.

## Paraphrase-variance checks

Every environment currently has exactly one prompt template per arm. A
one-template design has no estimate of how much a result would move under a
differently-worded but equivalent instruction. Before treating any Stated-
vs-Artifact gap as a stable finding (rather than a property of this one
phrasing), run at least one paraphrase per arm and report the spread.

## Extending eval-awareness to Funding Email and Blackmail

`eval_aware`/`note_addressed` (see `docs/labeling.md`) are wired up for Eval
Tampering only so far. Funding Email already has its 60 completions
labeled — a retro-pass adding the awareness column (~20 minutes) would
complete the env×arm table this covariate is meant to support. Not started.

## Expansion to sufficient power

The Funding Email pilot's primary A-vs-B test is honestly underpowered at
n=30/arm (95% CI on the difference spans both "no effect" and most of the
published gap). The locked expansion prereg targeting n=150/arm has been run:
the original `moonshotai`-only provider pin 404'd at zero cost, was
re-verified live, and re-launched on a confirmed route (DeepInfra); all 300
calls completed cleanly. Generation and secondary judge grading are done.
What's still open is the prereg's primary human labeling of the stratified
98-record audit subset, see `docs/findings.md` and
`docs/handoff/funding_email_v2_disputes_resolved.md`.
