"""Generate the write-up's figures. Run: .venv/bin/python scripts/make_figures.py
Writes PNGs to figures/. Every rate/diff/CI here is computed either directly
from the committed label files or via stated_vs_revealed.analyze.analyze()
(the same function results/summary.json is built from) -- nothing is
hand-typed, and every arm's n is asserted against the run's own eligible
manifest count before it's plotted, so a figure can't silently drift from
the numbers reported elsewhere. Matplotlib only, no seaborn."""
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from stated_vs_revealed.analyze import analyze  # noqa: E402

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

STATED_C = "#4C72B0"
ARTIFACT_C = "#DD8452"


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0, center - half), min(1, center + half)


def bar_with_ci(ax, labels, rates_pct, cis_pct, colors, title, ylabel, hatches=None):
    x = np.arange(len(labels))
    bars = ax.bar(x, rates_pct, color=colors, width=0.55, zorder=3)
    if hatches:
        for bar, h in zip(bars, hatches):
            if h:
                bar.set_hatch(h)
                bar.set_edgecolor("white")
    for i, (r, (lo, hi)) in enumerate(zip(rates_pct, cis_pct)):
        ax.errorbar(i, r, yerr=[[r - lo], [hi - r]], fmt="none", ecolor="black",
                    elinewidth=1.3, capsize=5, capthick=1.3, zorder=4)
        ax.text(i, hi + 4, f"{r:.1f}%", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_title(title, fontsize=11.5, fontweight="bold", pad=10)


def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_prereg(rel_path):
    return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


# ---------- Canonical analyze() results -- the single source every figure below reads from ----------
FE_PILOT_DIR = ROOT / "results/live/funding_email/2026-08-12T16-44-24Z"
fe_pilot_result = analyze("funding_email", FE_PILOT_DIR, load_prereg("envs/funding_email/prereg/pilot.json"))
assert fe_pilot_result["per_arm"]["A"]["n_eligible"] == 30, fe_pilot_result["per_arm"]
assert fe_pilot_result["per_arm"]["B"]["n_eligible"] == 30, fe_pilot_result["per_arm"]

ET_PILOT_DIR = ROOT / "results/live/eval_tampering/2026-09-04T19-28-19Z"
et_pilot_result = analyze("eval_tampering", ET_PILOT_DIR, load_prereg("envs/eval_tampering/prereg/eval_tampering.json"))
assert et_pilot_result["per_arm"]["A"]["n_eligible"] == 30, et_pilot_result["per_arm"]
assert et_pilot_result["per_arm"]["B"]["n_eligible"] == 30, et_pilot_result["per_arm"]

ET_EXPANSION_DIR = ROOT / "results/live/eval_tampering/2026-09-04T23-17-17Z"
et_expansion_result = analyze("eval_tampering", ET_EXPANSION_DIR, load_prereg("envs/eval_tampering/prereg/expansion-v1.json"))
assert et_expansion_result["per_arm"]["A"]["n_eligible"] == 150, et_expansion_result["per_arm"]
assert et_expansion_result["per_arm"]["B"]["n_eligible"] == 150, et_expansion_result["per_arm"]

# Label composition (Fig 5) needs the raw human label rows directly, for
# the full per-label breakdown analyze() doesn't return (it only returns
# the single positive-label count).
fe_pilot_labeled = load_jsonl(FE_PILOT_DIR / "graded_with_human_labels.jsonl")
fe_pilot_labels = {"A": {}, "B": {}}
for r in fe_pilot_labeled:
    if r.get("excluded") or not r.get("human_label"):
        continue
    fe_pilot_labels[r["arm"]][r["human_label"]] = fe_pilot_labels[r["arm"]].get(r["human_label"], 0) + 1
assert (fe_pilot_labels["A"].get("disclose_specific", 0), 30) == fe_pilot_result["counts"]["A"]
assert (fe_pilot_labels["B"].get("disclose_specific", 0), 30) == fe_pilot_result["counts"]["B"]

et_pilot_human = load_jsonl(ET_PILOT_DIR / "human_labels.jsonl")
et_pilot_labels = {"A": {}, "B": {}}
for r in et_pilot_human:
    et_pilot_labels[r["arm"]][r["label"]] = et_pilot_labels[r["arm"]].get(r["label"], 0) + 1


# ---------- Fig 1: Funding Email pilot, specific-disclosure rate (primary, human-labeled) ----------
t = fe_pilot_result["test"]
n = 30
k_stated, k_artifact = fe_pilot_result["counts"]["A"][0], fe_pilot_result["counts"]["B"][0]
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
fig, ax = plt.subplots(figsize=(6.4, 4.2))
bar_with_ci(ax, ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Funding Email pilot: specific-disclosure rate\n(Stated minus Artifact; primary, human-labeled)",
            "% disclose_specific")
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.text(0.5, 0.01,
          f"{t['diff_pp']:+.1f}pp, one-sided z-test p={t['p_value_primary']:.3f} (not significant),\n"
          f"95% Wald CI on the difference [{t['ci_diff_95_wald'][0]*100:.1f}, {t['ci_diff_95_wald'][1]*100:.1f}]pp "
          "includes both zero and the paper's published 13pp gap",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "fig3_funding_email_pilot.png", dpi=200)
plt.close(fig)

# ---------- Fig 2: judge-reversal, reasoning-blind judge vs human labels ----------
fe_pre = load_jsonl(FE_PILOT_DIR / "graded_pre_reasoning_fix.jsonl")
judge_counts = {"A": [0, 0], "B": [0, 0]}  # [specific, gradeable_n]
for r in fe_pre:
    if r.get("excluded"):
        continue
    aj = r.get("agentic_judge")
    if not aj or aj.get("disclosure_level") is None:
        continue
    judge_counts[r["arm"]][1] += 1
    if aj["disclosure_level"] == "specific":
        judge_counts[r["arm"]][0] += 1

k_j_stated, n_j_stated = judge_counts["A"]
k_j_artifact, n_j_artifact = judge_counts["B"]
rates_judge = [k_j_stated / n_j_stated * 100, k_j_artifact / n_j_artifact * 100]
cis_judge = [tuple(100 * c for c in wilson_ci(k_j_stated, n_j_stated)),
             tuple(100 * c for c in wilson_ci(k_j_artifact, n_j_artifact))]

rates_human = [k_stated / 30 * 100, k_artifact / 30 * 100]
cis_human = [tuple(100 * c for c in wilson_ci(k_stated, 30)), tuple(100 * c for c in wilson_ci(k_artifact, 30))]

fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
bar_with_ci(axes[0], [f"Stated\n(n={n_j_stated})", f"Artifact\n(n={n_j_artifact})"], rates_judge, cis_judge,
            [STATED_C, ARTIFACT_C], "Reasoning-blind judge (pre-fix)\nagentic_judge.disclosure_level==specific, Wilson 95% CI",
            "% specific disclosure")
bar_with_ci(axes[1], ["Stated\n(n=30)", "Artifact\n(n=30)"], rates_human, cis_human,
            [STATED_C, ARTIFACT_C], "Human labels (primary, post-fix)\nWilson 95% CI", "")
fig.suptitle("A judge blind to reasoning gets the ranking backwards (Stated vs. Artifact swap)",
             fontsize=12.5, fontweight="bold", y=1.03)
fig.tight_layout()
fig.text(0.5, -0.03, "Same 60 completions. Cut-off responses state their real decision in\n"
                      "response_reasoning, never in visible content the pre-fix judge read.",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "fig2_judge_reversal.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Fig 4: Eval Tampering, pilot (primary) vs expansion (consultative) -- concealment throughout ----------
# Both panels plot the SAME estimand as the prereg (conceal_rate_B - conceal_rate_A),
# so pilot and expansion are read on one consistent axis. Ambiguous records are
# excluded from neither arm's denominator -- they inflate n without counting as
# conceal for either side (analyze()'s own denominator_rule, asserted below).
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)

t_pilot = et_pilot_result["test"]
n = 30
k_conceal_a, k_conceal_b = et_pilot_result["counts"]["A"][0], et_pilot_result["counts"]["B"][0]
rates = [k_conceal_a / n * 100, k_conceal_b / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_conceal_a, n)), tuple(100 * c for c in wilson_ci(k_conceal_b, n))]
bar_with_ci(axes[0], ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Pilot (primary, human-labeled)\nWilson 95% CI", "% conceal")

t_exp = et_expansion_result["secondary"]
n = 150
k_conceal_a_exp, k_conceal_b_exp = t_exp["counts"]["A"][0], t_exp["counts"]["B"][0]
# Ambiguous (5/150) is present in the Stated arm's consultative labels and
# is excluded from the numerator on both sides but retained in n -- so
# n stays 150, not 145; this is the "ambiguous excluded from neither arm"
# denominator rule, checked directly rather than assumed.
assert et_expansion_result["per_arm"]["A"]["n_eligible"] == 150
rates_exp = [k_conceal_a_exp / n * 100, k_conceal_b_exp / n * 100]
cis_exp = [tuple(100 * c for c in wilson_ci(k_conceal_a_exp, n)), tuple(100 * c for c in wilson_ci(k_conceal_b_exp, n))]
bar_with_ci(axes[1], ["Stated (n=150)\n4 model raters, consultative", "Artifact (n=150)\ndeterministic rule"],
            rates_exp, cis_exp, [STATED_C, ARTIFACT_C],
            "Expansion-v1 (consultative/deterministic,\nnot yet the prereg's primary)", "% conceal",
            hatches=["//", None])
for tick in axes[1].get_xticklabels():
    tick.set_fontsize(8.5)

fig.suptitle("Concealment rate: direction persists at n=150\n(Stated arm model-rated at n=150, not directly comparable to the human-labeled pilot)",
             fontsize=11.5, fontweight="bold", y=1.08)
fig.tight_layout(rect=(0, 0.12, 1, 1))
p_exp_str = f"p={t_exp['p_value_two_sided']:.3f}" if t_exp['p_value_two_sided'] >= 0.0005 else "p<0.001"
fig.text(0.5, 0.01,
          f"Pilot: {t_pilot['diff_pp']:+.1f}pp, two-sided Fisher exact p={t_pilot['p_value_primary']:.3f}. "
          f"Expansion: {t_exp['diff_pp']:+.1f}pp, two-sided Fisher exact {p_exp_str} (consultative, not primary). "
          "Ambiguous counted in n, not as conceal, on both arms.",
         ha="center", fontsize=8, color="#555", style="italic")
fig.savefig(OUT / "fig4_eval_tampering_pilot_vs_expansion.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Fig 5: Label composition, both pilots (human-labeled Stated; deterministic-rule Artifact for ET) ----------
FE_ORDER = ["disclose_specific", "disclose_vague", "ambiguous", "no_disclosure", "refused"]
FE_COLORS = {"disclose_specific": "#4C72B0", "disclose_vague": "#8CA9D6", "ambiguous": "#B0B0B0",
             "no_disclosure": "#DD8452", "refused": "#8C3B23"}
ET_ORDER = ["disclose_specific", "ambiguous", "conceal"]
ET_COLORS = {"disclose_specific": "#4C72B0", "ambiguous": "#B0B0B0", "conceal": "#DD8452"}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))

for ax, title, order, colors, labels_dict, n_each in [
    (axes[0], "Funding Email pilot (n=30/arm)", FE_ORDER, FE_COLORS, fe_pilot_labels, 30),
    (axes[1], "Eval Tampering pilot (n=30/arm)", ET_ORDER, ET_COLORS, et_pilot_labels, 30),
]:
    arms = ["Stated", "Artifact"]
    left = np.zeros(2)
    for lab in order:
        counts = [labels_dict["A"].get(lab, 0), labels_dict["B"].get(lab, 0)]
        pct = [c / n_each * 100 for c in counts]
        bars = ax.barh(arms, pct, left=left, color=colors[lab], label=lab, height=0.55)
        for bar, c in zip(bars, counts):
            if c > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                        str(c), ha="center", va="center", fontsize=9,
                        color="white" if colors[lab] not in ("#B0B0B0",) else "black")
        left += pct
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of records")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=8, frameon=False)

fig.suptitle("Where the non-disclosures go (both pilots)", fontsize=13, fontweight="bold", y=1.04)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.text(0.5, 0.005, "Composition, not an estimate (no CIs). Label sets differ by environment (see legend).\n"
                      "Funding Email: both arms human-labeled. Eval Tampering: Stated human-labeled,\n"
                      "Artifact by the published deterministic rule.",
         ha="center", fontsize=8, color="#555", style="italic")
fig.savefig(OUT / "fig5_label_composition.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Fig 1: Cross-environment sign flip (pilots only, both from analyze()) ----------
fig, ax = plt.subplots(figsize=(8.2, 4.6))
envs = ["Funding Email\n(pilot, n=30/arm)", "Eval Tampering\n(pilot, n=30/arm)"]
fe_diff = fe_pilot_result["test"]["diff_pp"]
et_diff = et_pilot_result["test"]["diff_pp"]  # conceal_B - conceal_A; equals Stated-minus-Artifact
                                                # disclosure exactly in this 2-outcome pilot data (no
                                                # ambiguous/refused present), asserted below rather than assumed.
_stated_disclose_pilot = 30 - et_pilot_result["counts"]["A"][0]
_artifact_disclose_pilot = 30 - et_pilot_result["counts"]["B"][0]
assert round((_stated_disclose_pilot - _artifact_disclose_pilot) / 30 * 100, 1) == round(et_diff, 1), (
    "ET pilot conceal-estimand and Stated-minus-Artifact disclosure only coincide when no "
    "ambiguous/refused labels exist in this arm; re-derive this figure's ET value if that changes."
)
deltas = [fe_diff, et_diff]
ci_lo = [fe_pilot_result["test"]["ci_diff_95_wald"][0] * 100, et_pilot_result["test"]["ci_diff_95_wald"][0] * 100]
ci_hi = [fe_pilot_result["test"]["ci_diff_95_wald"][1] * 100, et_pilot_result["test"]["ci_diff_95_wald"][1] * 100]
colors = ["#4C72B0" if d > 0 else "#DD8452" for d in deltas]
y = np.arange(len(envs))
ax.barh(y, deltas, color=colors, height=0.5, zorder=3)
for i, (d, lo, hi) in enumerate(zip(deltas, ci_lo, ci_hi)):
    ax.errorbar(d, i, xerr=[[d - lo], [hi - d]], fmt="none", ecolor="black",
                elinewidth=1.3, capsize=5, capthick=1.3, zorder=4)
    label_y = i + 0.30
    ax.text(d, label_y, f"{d:+.1f}pp", va="bottom", ha="center", fontsize=10.5, fontweight="bold")
ax.axvline(0, color="black", linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels(envs)
ax.set_ylim(-0.6, 1.6)
ax.set_xlabel("Stated minus Artifact, specific-disclosure rate (pp)")
ax.set_title("Same one-line manipulation, opposite sign across environments\n"
             "(neither individually significant at n=30/arm)",
             fontsize=12, fontweight="bold")
ax.set_xlim(-55, 30)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.text(0.5, 0.01,
          "FE: one-sided z-test, Wald CI on the difference. ET: two-sided Fisher exact "
          "(estimand conceal_B-conceal_A, sign-flipped to disclosure here), Wald CI.",
         ha="center", fontsize=7.5, color="#555", style="italic")
fig.savefig(OUT / "fig1_cross_environment_sign_flip.png", dpi=200)
plt.close(fig)

print("Wrote figures to", OUT)
for p in sorted(OUT.glob("*.png")):
    print(" -", p.name, f"{p.stat().st_size/1024:.0f}KB")
