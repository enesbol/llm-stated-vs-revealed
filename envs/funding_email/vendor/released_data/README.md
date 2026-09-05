# vendor/released_data/

Two batches from the Hugging Face dataset `Model-Forensics/model-forensics`
at revision `e9aa97a7aac835b56b67e28746429d57730b3bdb` (full provenance:
`PROVENANCE.md` §3). Split into two tiers so the repo's default footprint
stays small without losing anything reproducible.

## Core tier (committed, verified via `MANIFEST.sha256`)

```
2026-02-20_14-55-00/config.json              2026-02-20_15-11-05/config.json
2026-02-20_14-55-00/grading_results.json     2026-02-20_15-11-05/grading_results.json
```

4 files. This is all the primary reproduction needs: `config.json` carries
the exact, byte-literal Arm A prompt (the anchor `run.py` hashes against);
`grading_results.json` carries the published per-sample judge labels, whose
aggregate is exactly the published 78/100 and 77/100 counts.

## Samples tier (gitignored, fetch-on-demand)

```
2026-02-20_14-55-00/sample-0/result.json ... sample-99/result.json
2026-02-20_15-11-05/sample-0/result.json ... sample-99/result.json
```

200 files — the individual raw model completions. Only needed for the
secondary, already-caveated-as-unverified contamination/manipulation-check
reproduction. Not vendored by default to keep the repo's committed surface
small; fetch them with:

```bash
python -m stated_vs_revealed.fetch --fetch --samples
```

Every file, once fetched, is checked against the git blob SHA-1 recorded in
`VERIFICATION.md` (the same hash scheme GitHub and Hugging Face both use for
non-LFS files): `python -m stated_vs_revealed.fetch --verify --samples`.
Their absence is not a verification failure; `--verify` (no `--samples`)
only checks the core tier and passes on a fresh clone with zero network
access.
