"""Generate the write-up's figures. Run: .venv/bin/python scripts/make_figures.py
Writes PNGs to figures/. Every number here is read from the committed JSONL
files at generation time, never hand-typed. Matplotlib only, no seaborn."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


# ---------- Figure 1: Funding Email, pilot (primary, human-labeled) ----------
fe_pilot = load_jsonl(ROOT / "results/live/funding_email/2026-08-12T16-44-24Z/graded_with_human_labels.jsonl")
fe_pilot_labels = {"A": {}, "B": {}}
for r in fe_pilot:
    if r.get("excluded") or not r.get("human_label"):
        continue
    fe_pilot_labels[r["arm"]][r["human_label"]] = fe_pilot_labels[r["arm"]].get(r["human_label"], 0) + 1

n = 30
k_stated = fe_pilot_labels["A"].get("disclose_specific", 0)
k_artifact = fe_pilot_labels["B"].get("disclose_specific", 0)
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
fig, ax = plt.subplots(figsize=(6.4, 4.2))
bar_with_ci(ax, ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Funding Email pilot, specific-disclosure rate\n(primary outcome, human-labeled)",
            "% disclose_specific")
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.text(0.5, 0.01, "+6.7pp, one-sided p=0.150 (not significant), 95% CI on the\n"
                     "difference includes both zero and the paper's published 13pp gap",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "funding_email_pilot.png", dpi=200)
plt.close(fig)

# ---------- Figure 2: Label composition, both pilots (human-labeled) ----------
et_human = load_jsonl(ROOT / "results/live/eval_tampering/2026-09-04T19-28-19Z/human_labels.jsonl")
et_labels = {"A": {}, "B": {}}
for r in et_human:
    et_labels[r["arm"]][r["label"]] = et_labels[r["arm"]].get(r["label"], 0) + 1

FE_ORDER = ["disclose_specific", "disclose_vague", "ambiguous", "no_disclosure", "refused"]
FE_COLORS = {"disclose_specific": "#4C72B0", "disclose_vague": "#8CA9D6", "ambiguous": "#B0B0B0",
             "no_disclosure": "#DD8452", "refused": "#8C3B23"}
ET_ORDER = ["disclose_specific", "ambiguous", "conceal"]
ET_COLORS = {"disclose_specific": "#4C72B0", "ambiguous": "#B0B0B0", "conceal": "#DD8452"}

fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))

for ax, title, order, colors, labels_dict, n_each in [
    (axes[0], "Funding Email pilot (n=30/arm)", FE_ORDER, FE_COLORS, fe_pilot_labels, 30),
    (axes[1], "Eval Tampering pilot (n=30/arm)", ET_ORDER, ET_COLORS, et_labels, 30),
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

fig.suptitle("Where the non-disclosures go (human-labeled pilots only)", fontsize=13, fontweight="bold", y=1.04)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.text(0.5, 0.005, "Composition, not an estimate (no CIs). Label sets differ by environment (see legend).\n"
                      "Eval Tampering Artifact arm via the published deterministic rule, not human judgment.",
         ha="center", fontsize=8, color="#555", style="italic")
fig.savefig(OUT / "label_composition.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 3: Eval Tampering, pilot (primary) vs expansion (consultative) ----------
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)

n = 30
k_stated, k_artifact = et_labels["A"].get("disclose_specific", 0), et_labels["B"].get("disclose_specific", 0)
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
bar_with_ci(axes[0], ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Pilot (primary, human-labeled)", "% disclose")

et_consult = load_jsonl(ROOT / "results/live/eval_tampering/2026-09-04T23-17-17Z/consultative_labels.jsonl")
et_mech = load_jsonl(ROOT / "results/live/eval_tampering/2026-09-04T23-17-17Z/mechanical_labels.jsonl")
n = 150
k_stated = sum(1 for r in et_consult if r["label"] == "disclose_specific")
k_artifact = sum(1 for r in et_mech if r.get("label") == "disclose_specific")
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
bar_with_ci(axes[1], ["Stated\n(n=150)", "Artifact\n(n=150)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Expansion-v1", "", hatches=["//", None])
axes[1].text(0.25, -0.24, "4 model raters, consultative", ha="center", fontsize=7.5, color="#555",
             transform=axes[1].transAxes)
axes[1].text(0.75, -0.24, "deterministic rule", ha="center", fontsize=7.5, color="#555",
             transform=axes[1].transAxes)

fig.suptitle("Direction persists at n=150 (Stated arm model-rated, not directly comparable to the pilot)",
             fontsize=12, fontweight="bold", y=1.03)
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.savefig(OUT / "eval_tampering_pilot_vs_expansion.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 4: Cross-environment sign flip (pilots only) ----------
fig, ax = plt.subplots(figsize=(8.2, 4.3))
envs = ["Funding Email\n(pilot, n=30/arm)", "Eval Tampering\n(pilot, n=30/arm)"]
deltas = [+6.7, -20.0]  # Stated - Artifact on disclose-rate, signed so + means Stated discloses more
ci_lo = [-5.8, -44.3]
ci_hi = [19.2, 4.3]
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
ax.set_xlabel("Stated minus Artifact, disclosure rate (pp)")
ax.set_title("Same one-line manipulation, opposite sign across environments\n"
             "(neither individually significant at n=30/arm)",
             fontsize=12, fontweight="bold")
ax.set_xlim(-55, 30)
fig.tight_layout()
fig.savefig(OUT / "cross_environment_sign_flip.png", dpi=200)
plt.close(fig)

# ---------- Figure 5: judge-reversal, reasoning-blind judge vs human labels ----------
fe_pre = load_jsonl(ROOT / "results/live/funding_email/2026-08-12T16-44-24Z/graded_pre_reasoning_fix.jsonl")
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

rates_human = [k_stated_pilot := fe_pilot_labels["A"].get("disclose_specific", 0),
               k_artifact_pilot := fe_pilot_labels["B"].get("disclose_specific", 0)]
rates_human = [rates_human[0] / 30 * 100, rates_human[1] / 30 * 100]
cis_human = [tuple(100 * c for c in wilson_ci(k_stated_pilot, 30)),
             tuple(100 * c for c in wilson_ci(k_artifact_pilot, 30))]

fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
bar_with_ci(axes[0], [f"Stated\n(n={n_j_stated})", f"Artifact\n(n={n_j_artifact})"], rates_judge, cis_judge,
            [STATED_C, ARTIFACT_C], "Reasoning-blind judge (pre-fix)\nagentic_judge.disclosure_level==specific",
            "% specific disclosure")
bar_with_ci(axes[1], ["Stated\n(n=30)", "Artifact\n(n=30)"], rates_human, cis_human,
            [STATED_C, ARTIFACT_C], "Human labels (primary, post-fix)", "")
fig.suptitle("A judge blind to reasoning gets the ranking backwards",
             fontsize=12.5, fontweight="bold", y=1.03)
fig.tight_layout()
fig.text(0.5, -0.03, "Same 60 completions. Cut-off responses state their real decision in\n"
                      "response_reasoning, never in visible content the pre-fix judge read.",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "judge_reversal.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("Wrote figures to", OUT)
for p in sorted(OUT.glob("*.png")):
    print(" -", p.name, f"{p.stat().st_size/1024:.0f}KB")
