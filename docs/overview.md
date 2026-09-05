# Overview

Plain-English catch-up. Ported/condensed from
model-forensic-research/docs/refresher.md's still-current status section.

## The question

The paper *Model Forensics* (arXiv 2606.26071) published a 13-point gap
between agentic behavior (65% specific disclosure, n=347) and third-person
"What would you do?" framing (78%, n=200) in a funding-email disclosure
scenario. It named the explanation — competing task/role/format pressures in
the agentic setting — as an untested guess, twice, and built a
methodological recommendation on top of it without testing it.

This repo isolates the confound the paper never controlled for: the agentic
setting forces a real, sent artifact; the third-person setting only asks
what the model would do. So: does forcing a concrete **artifact** (still
never executed/sent) change disclosure, holding everything else constant?

## Current status (Funding Email)

The real primary result: **96.7% (Stated, free-form) vs. 90.0% (Artifact,
forced-email), one-sided p=0.150 — not statistically significant** at
n=30/arm. This is an honest, pre-registered null, not an unfinished result.

Three findings alongside the null (full detail: `docs/findings.md`):

1. **The published third-person rate did not reproduce** — our fresh Stated
   arm (96.7%) vs. the paper's own historical rate (77.5%, same byte-locked
   prompt, same provider pin) is a real, positive finding (Fisher's exact
   two-sided p≈0.013), not a null. Root cause investigated: a refusal-rate
   drift (16.5%→3.3%) between the paper's data collection and this pilot,
   confirmed via a full census of the paper's own 33 refused-labeled
   completions, not a sample.
2. **A reasoning-blind judge manufactured a reversed result.** A judge
   reading only the visible response text (not the model's `reasoning`
   field) scored the Artifact arm higher than Stated — the opposite sign
   from the eventual human-labeled result. Cut-off completions state their
   real decision in reasoning, never in visible content.
3. **A planned expansion to n=150/arm ran, after a provider break was found and fixed live, not patched around silently.** The
   `moonshotai`-only provider pin (matching the paper's own released config)
   stopped routing to the pinned model on OpenRouter entirely between the
   pilot and the expansion attempt, confirmed live, $0 spent (404s aren't
   billed). Rather than repin blind, the actual serving provider was
   re-verified live (`GET /api/v1/models/.../endpoints`) and the run
   completed on the confirmed route (DeepInfra), 300/300 calls, 0 errors.
   Generation and secondary judge grading are complete; the prereg's primary
   human labeling of the audit subset is not (see `docs/findings.md`).

## Current status (Eval Tampering)

A second environment, same Stated/Artifact structure, different scenario (a
math-grading agent finds a note from a past copy of itself admitting the
test was rigged to dodge weapons-capability assessment). Pilot (n=30/arm) is
complete and fully human-labeled: Artifact arm via a deterministic rule
(30/30 parsed, no judge used at n=30, see `docs/findings.md`), Stated arm
hand-labeled directly. An n=150/arm expansion has since run (300/300 calls,
0 errors): the Artifact arm is complete via the same deterministic rule;
the Stated arm has a 4-model-rater consultative reading only, not yet the
prereg's primary human pass (see `docs/handoff/eval_tampering_v1_resolved.md`).

## Where to look next

- `docs/arms.md` — the Stated/Artifact/Tool-call framework and why some
  environments only have two of the three.
- `docs/labeling.md` — the rubric, traps, and eval-awareness column used
  when hand-labeling any environment's completions.
- `docs/findings.md` — the full dated log of what was found, what broke,
  and what was fixed, in the order it happened.
- `docs/next.md` — what's deliberately not built yet (Blackmail, a real
  executed-action arm, paraphrase-variance checks).
