# Provenance

**A note on paths below:** this file's prose was originally written for an
earlier, differently-laid-out repo (`model-forensic-research`) and later
carried into this one; most of it was updated, a few self-references to our
own code weren't. Where a path below names something we wrote, it means the
current layout unless it's inside a quoted/historical passage describing
that earlier repo specifically:

| Old (`model-forensic-research`) | Current (this repo) |
|---|---|
| `src/ours/` | `src/stated_vs_revealed/` |
| `src/ours/fetch_and_verify.py` | `src/stated_vs_revealed/fetch.py` (`python -m stated_vs_revealed.fetch`) |
| `src/ours/run_experiment.py` | `src/stated_vs_revealed/run.py` (`python -m stated_vs_revealed.run`) |
| `CLAUDE.md` (repo rules doc) | no equivalent single file here; Arm-A byte-fidelity is enforced by `tests/envs/test_funding_email_prompt_diff.py` |
| `preregistration/` | `envs/<name>/prereg/` |

Every file under `vendor/` is copied byte-for-byte from a public upstream source at a
pinned commit or dataset revision. Nothing under `vendor/` is edited, reformatted, or
regenerated. Verification method for every file: the downloaded content's SHA-256 is
recorded in `MANIFEST.sha256` (run `sha256sum -c MANIFEST.sha256` to check), and during
vendoring every file was additionally cross-checked against the source host's own
recorded blob hash (GitHub git blob SHA-1 / Hugging Face `oid`, which use the same
`git hash-object` scheme) — see "Independent verification" below.

## 1. `gkroiz/model_forensics_paper` — commit `abb5fac45f19e91d8356b2f9cc63284cfd8f1bde`

Source: https://github.com/gkroiz/model_forensics_paper/tree/abb5fac45f19e91d8356b2f9cc63284cfd8f1bde

| Local path | Upstream path | GitHub blob SHA-1 |
|---|---|---|
| `vendor/model_forensics_paper/api.py` | `src/model_incrimination_paper/api.py` | `bd88bf3e5cf109bac665db5ccc605c07799feca6` |
| `vendor/model_forensics_paper/pyproject.toml` | `pyproject.toml` | `514c594e6054ce8256805acf963f0983a51fdbcc` |

No `LICENSE` file exists in this repository (confirmed via `GET /repos/gkroiz/model_forensics_paper/license` → 404, and by listing the repo tree at the pinned commit).

`vendor/model_forensics_paper/api.py`'s own commit history in this repo starts
2026-05-02 — after the Feb 2026 funding_email experiment. Its `temperature=1.0` /
`top_p=1.0` / `max_tokens=16000` defaults cannot be attributed to the original
third-person generation call; they are not contemporaneous with it.

Repo root also contains a `reproduce/` directory; `reproduce/REQUIRED_RESULTS.md`
lists Currency Conversion, Sandbagging, Eval Tampering, Secret Number, Precommit
Hook — no `funding_email`, and `download_results.py` is an unfinished stub ending in
`raise NotImplementedError`. No in-repo path to regenerate the published 65%
agentic-arm number from this repo. We do not vendor `reproduce/` (Arm A/B never
re-runs the agentic arm — see `README.md` § Scope).

`main.tex` (fetched directly, not vendored) states the agentic 65% is drawn from
**347 non-eval-aware runs**, with a separate 28 eval-aware runs excluded from all
downstream analysis (375 total). Its Appendix (`app:env:funding_email`) system
prompt lists **four** tools (`execute_command`, `update_email`, `send_email`,
`end_session`) — no `cancel_email`. The real agentic rollouts in the HF dataset (§3)
show a **five**-tool system prompt (adds `cancel_email`, disabled via
`allow_cancel_email: false`) — confirmed directly against a real `rollout.log`. The
65%-vs-78% comparison therefore differs in tool affordances shown to the model, not
only in agentic-vs-third-person framing — this is a confound in the PAPER's own
comparison, distinct from this project's Arm A/B (§ below), which holds the
environment representation fixed and swaps only the terminal instruction.

Agentic-side sampling, from `gkroiz/agent-interp-envs` (real env harness, not
vendored — src §2): `openrouter_provider.py` omits `temperature`/`top_p` when not
explicitly passed; `environments/funding_email/agent.py` never passes them either.
A real per-run `config.yaml` (`2026-02-08_10-52-37`) confirms no temperature/top_p/
max_tokens/reasoning_effort fields set — `provider_preferences.only: [moonshotai]`
and `max_steps: 20` are the only generation-relevant fields present. **A specific
claim of `max_tokens=32000` / `reasoning.effort="high"` for these runs does not hold
up** — checked via GitHub code search across the full `agent-interp-envs` repo: zero
hits for "32000"; the provider's actual default reasoning effort is `"xhigh"`, never
overridden by any funding_email config. Do not cite 32000/"high" as historical
parameters.

OpenRouter's provider routing is itself not a frozen historical record: routing
among backends for a given model slug is dynamic and provider-availability-dependent
(OpenRouter's own provider-routing docs), so even a pinned model string is not a
guarantee of matching February 2026 serving behavior today. Both sides pin
`provider_preferences.only: [moonshotai]` (confirmed: third-person `config.json` has
the identical field) — this narrows but does not eliminate the gap, since Moonshot's
own backend behavior for that model slug is not itself frozen in the historical
record either.

## 2. `gkroiz/investigating-model-motives-blog` — commit `b36a8bc287e7d5c219d2bd50869397364a5ffb92`

Source: https://github.com/gkroiz/investigating-model-motives-blog/tree/b36a8bc287e7d5c219d2bd50869397364a5ffb92

| Local path | Upstream path | GitHub blob SHA-1 |
|---|---|---|
| `vendor/prompts/PROMPT_TEMPLATES.md` | `funding_email_details/PROMPT_TEMPLATES.md` | `20bc519afa9b6c838fddb1c7460448e9e09a32c0` |
| `vendor/prompts/funding_email_README.md` | `funding_email_details/README.md` | `2916a264b574116157af62d367014ea1206f264f` |
| `vendor/prompts/legal_review_variants/01_baseline.md` | `funding_email_details/legal_review_variants/01_baseline.md` | `2957a86200a54872b0d9cc18bc614e896116043d` |
| `vendor/prompts/workspace_files/cost_analysis.md` | `funding_email_details/workspace_files/cost_analysis.md` | `e7f387bcafa40607f151bf156653ce3f3579a316` |
| `vendor/prompts/workspace_files/customer_feedback.md` | `funding_email_details/workspace_files/customer_feedback.md` | `f0ffdf19fd46a7cd8f046a624fb22776123c8de7` |
| `vendor/prompts/workspace_files/field_trials_summary.md` | `funding_email_details/workspace_files/field_trials_summary.md` | `92f3a6da2989f3fba97ef31e323ca16f638fd24b` |
| `vendor/prompts/workspace_files/performance_benchmarks.md` | `funding_email_details/workspace_files/performance_benchmarks.md` | `0ae98fe90e300762f3d295aa64ba84d1fd14fb73` |
| `vendor/prompts/workspace_files/technical_specifications.md` | `funding_email_details/workspace_files/technical_specifications.md` | `45151df9f2ab1b5fc72db9a21807ec25f221d571` |
| `vendor/prompts/workspace_files/scheduled_emails/investor_email_draft.txt` | `funding_email_details/workspace_files/scheduled_emails/investor_email_draft.txt` | `35d1aec07e240f9389c4ec63d99dc112667d0b5f` |

We vendored only the `workspace_files/` set (the baseline Myanmar-surveillance
condition, matching `legal_review_variants/01_baseline.md`), not the parallel
`tobacco_workspace_files/` set or the other 18 `legal_review_variants/*` counterfactual
files — those belong to other conditions the P5-final design does not run.

No `LICENSE` file exists in this repository either (confirmed by listing the full repo
tree at the pinned commit: 135 blobs, none named `LICENSE*`).

This repo's `funding_email_details/README.md` describes the Myanmar/Rakhine/Rohingya
scenario throughout, matching the vendored `legal_review_variants/01_baseline.md`
(verified: no "Xinjiang" string anywhere in `vendor/prompts/funding_email_README.md`).

**`gkroiz/agent-interp-envs`** (not vendored here, not in `MANIFEST.sha256`) is the
real environment harness that produced the agentic rollouts in §3 below —
`environments/funding_email/{agent.py,tools.py,run_step.py,states.py}` and
`configs/funding_email/default.yaml`. Its own README (Xinjiang/PRC framing, an
earlier/parallel variant of this scenario, not the Myanmar one used everywhere else
in this project) and its `agent.py` (confirmed: does not pass `temperature`/`top_p`
to the provider) are both real, checked directly via `gh api`. Nothing from this
repo is copied into `src/stated_vs_revealed/` or `vendor/`; it's cited here only as the source of
the tool-list and sampling-parameter facts above and in §3.

## 3. Hugging Face dataset `Model-Forensics/model-forensics` — revision `e9aa97a7aac835b56b67e28746429d57730b3bdb`

Source: https://huggingface.co/datasets/Model-Forensics/model-forensics/tree/e9aa97a7aac835b56b67e28746429d57730b3bdb/funding_email/ask_about_files

**Also present at this same revision, not vendored:** `funding_email/moonshotai-kimi-k2.5/`
— **68 dated batches** (confirmed directly via the HF tree API at `?limit=500`, no
pagination truncation; corrects an earlier "73" figure that was never independently
checked) of real per-run agentic rollouts (`rollout.log`, `config.yaml`,
`grading_results.json` per batch), sibling to the `ask_about_files/` subtree above.
The paper's own `main.tex` gives the target pool directly: **347 non-eval-aware + 28
eval-aware = 375 runs**, eval-aware excluded from all downstream analysis (§1).
**Manifest reconstruction attempted — narrowed, not solved:** fetched all 68
batches' `config.yaml`+`grading_results.json`, matched embedded `legal_review`
content against our vendored baseline (whitespace-normalized hash). 21/68 batches
carry the exact baseline content; filtering to default-recipient, no-audit-notes,
no-scenario-override, 5-tool-prompt leaves 4 candidate batches
(`2026-02-02_08-26-31`, `2026-02-02_08-34-14`, `2026-02-02_08-42-31`,
`2026-02-08_14-49-06`): 400 runs, 26 eval-aware, 374 non-eval-aware — close to
347/28/375 but not an exact match (off by ~25 raw runs). Full method, candidate
list, and the discarded early-pilot batch: `docs/funding_email_65pct_manifest.md`.
This repo's dataset namespace (`Model-Forensics/model-forensics`)
differs from the one named in the paper repo's `download_results.py`
(`adsingh64/model-forensics`); most likely an org rename/migration (this revision's
committer is `gkroiz`, a paper author) rather than a different dataset — not
independently confirmed.

Both batches vendored, split into two tiers (see `vendor/released_data/README.md`
for the full rationale — kept out of this file to avoid duplicating it):

- `funding_email/ask_about_files/2026-02-20_14-55-00/` → `vendor/released_data/2026-02-20_14-55-00/`
- `funding_email/ask_about_files/2026-02-20_15-11-05/` → `vendor/released_data/2026-02-20_15-11-05/`

**Core tier (committed, in `MANIFEST.sha256`):** `config.json` and
`grading_results.json` per batch — 4 files. This is everything the primary
77/100-and-78/100 reproduction needs.

**Samples tier (gitignored, fetch-on-demand via `python -m stated_vs_revealed.fetch --fetch
--samples`):** `sample-0/result.json` .. `sample-99/result.json` per batch —
200 files, the individual raw completions, needed only for the secondary
contamination/manipulation-check reproduction. **The actual on-disk layout is
`sample-N/result.json` (a directory per sample), not a flat `sample-N.json`
file** — verified directly against the Hugging Face tree API before
downloading anything. (An earlier note in this project's decision trace
claimed the layout was flat; that note was checked here and found incorrect
for this revision. `stated_vs_revealed.fetch` discovers the layout from the API
tree rather than hardcoding either shape, so this class of error can't
silently break the pipeline again.)

At vendoring time, every one of the 200 `sample-N/result.json` files, plus
both `config.json` and both `grading_results.json` files, was verified
against the Hugging Face API's recorded `oid` (git blob SHA-1) for that
path/revision — 204 files checked, 0 mismatches — before the samples tier
was moved out of the default committed tree. See
`vendor/released_data/VERIFICATION.md` for the full per-file check log; that
log is what `python -m stated_vs_revealed.fetch --verify --samples` re-checks against if
you fetch the samples tier later.

**Load-bearing facts extracted directly from these files (not re-derived from anyone's
prose summary):**
- `2026-02-20_15-11-05/config.json` contains the *exact, complete, byte-literal* prompt
  sent to the model for every sample in that batch (`messages[0].content`, 23,642
  characters, ending `"--- QUESTION ---\nWhat would you do?"`). This is the anchor
  `tests/envs/test_funding_email_prompt_diff.py` hashes Arm A against.
- `config.json` for both batches has an **identical** blob hash
  (`12679402790acc50d25e9cd115b704a1f7ece74e`) — the two batches are two independent
  100-sample draws from the literal same prompt/config, not two different conditions.
- Neither `config.json` sets `temperature`, `top_p`, or any sampling parameter — only
  `model`, `question`, `num_samples`, `provider_preferences`. The released 78%/77% rests
  on whatever the provider's default sampling was at run time in February 2026. This is
  Risk #6 in the P5-final design doc, now confirmed directly from the artifact rather
  than inferred.
- `2026-02-20_15-11-05/grading_results.json`: `stated_action_counts.disclose_specific =
  78` of 100. `2026-02-20_14-55-00/grading_results.json`: `disclose_specific = 77` of
  100. Pooled: 155/200 = 77.5%, matching the paper's published third-person rate.
- Both grading files record `judge_model: "google/gemini-3-pro-preview"` and
  `question: "What would you do?"`.

## 4. Missing upstream code — searched, not found

Per the task spec, before writing any replacement code we searched once for
`funding_email/ask_about_files.py` and `funding_email/judge_ask_about_files.py`
(the scripts `PROMPT_TEMPLATES.md` §3/§4 cite as their source but does not ship):

- Full recursive tree search of `gkroiz/model_forensics_paper` at the pinned commit,
  at `main`, and at every other branch (`gkroiz/dev`, `adsingh-64/dev`,
  `adsingh-64/appendices`, `adsingh-64/insights`, five `overleaf-*` branches): absent.
- Full recursive tree search of `gkroiz/investigating-model-motives-blog` at the pinned
  commit and at `main` (its only branch): absent.
- `gkroiz/agent-interp-envs` was independently checked for these filenames during the
  Aug 11 sweep (see `docs/Cowork.md` log entry B12) and found absent; not re-vendored
  here since the P5-final design is single-turn and does not run that environment.
- Full listing of every other public, non-fork repository under the `gkroiz` GitHub
  account (`syllabus-project`, `weatherDNN`, `principled-interp-blog`,
  `dynamic_user_attribute_study`, `gen_code_vulnerabilities`, `premarket-predictions`,
  `HMBLib`, `ray-on-gpu`, `gkroiz.github.io`, `copy-coder`, `crankshaw-NeMo`): none
  named or plausibly containing these scripts.
- Web search for `"ask_about_files.py" gkroiz`: no hit.
- GitHub's commit-search API for `ask_about_files` scoped to the paper repo: `0` results.

**Conclusion: absent from every public location searched.** We do not claim the
replacement code in `src/stated_vs_revealed/` is upstream author code. `src/stated_vs_revealed/run.py` builds
Arm A directly from the vendored, byte-verified `config.json` prompt (§3 above) rather
than reconstructing it from the redacted template in `PROMPT_TEMPLATES.md`, so the
missing script does not block prompt fidelity — only the batch *generation* logic
(sampling loop, retry handling, OpenRouter call shape) had to be written fresh, and it
is clearly new code under `src/stated_vs_revealed/`, license-scoped separately from `vendor/` (see
`LICENSE`).

## License scope

No upstream source vendored above ships its own LICENSE file (checked directly on all
three, § 1–3). `vendor/` therefore carries no redistribution license of its own; it is
reproduced here solely for research reproducibility, byte-identical to the public
source, with full attribution to the original authors (Singh, Kroiz, Rajamanoharan,
Nanda) and source URLs as listed above. The `LICENSE` file at repo root covers
`src/`, `tests/`, `scripts/`, `docs/`, `results/`, and each
`envs/*/{configs,prereg,rubric.md}` — everything written for this project —
and does NOT apply to anything under `envs/*/vendor/`.

**One carve-out inside `vendor/`:** each `envs/*/vendor/README.md` is project-authored
(it documents our own vendoring process, exact source commit/revision, and
verification method for that environment) even though it sits inside a `vendor/`
directory alongside byte-identical upstream material. These README files ARE covered
by `LICENSE`; the rest of each `vendor/` subtree is not.
