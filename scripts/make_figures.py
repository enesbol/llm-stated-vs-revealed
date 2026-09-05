"""Generate the write-up's figures. Run: .venv/bin/python scripts/make_figures.py
Writes PNGs to figures/. Matplotlib only, no seaborn dependency."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy import stats

OUT = Path(__file__).resolve().parents[1] / "figures"
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


def bar_with_ci(ax, labels, rates_pct, cis_pct, colors, title, ylabel):
    x = np.arange(len(labels))
    bars = ax.bar(x, rates_pct, color=colors, width=0.55, zorder=3)
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


# ---------- Figure 1: Funding Email -- pilot (primary, human-labeled) ----------
fig, ax = plt.subplots(figsize=(5.2, 4))
n = 30
k_stated, k_artifact = 29, 27
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
bar_with_ci(ax, ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Funding Email pilot -- specific-disclosure rate\n(primary outcome, human-labeled)",
            "% disclose_specific")
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.text(0.5, 0.01, "+6.7pp, one-sided p=0.150 (not significant) -- 95% CI on the\n"
                     "difference includes both zero and the paper's published 13pp gap",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "funding_email_pilot.png", dpi=200)
plt.close(fig)

# ---------- Figure 2: Funding Email -- expansion-v2, consultative ----------
fig, ax = plt.subplots(figsize=(5.2, 4))
n = 150
n_a, n_b = 83, 15  # audit subset sizes actually resolved
k_stated, k_artifact = 29, 11  # disclose_specific counts from the resolved consultative audit
rates = [k_stated / n_a * 100, k_artifact / n_b * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n_a)), tuple(100 * c for c in wilson_ci(k_artifact, n_b))]
bar_with_ci(ax, [f"Stated\n(n={n_a})", f"Artifact\n(n={n_b})"], rates, cis, [STATED_C, ARTIFACT_C],
            "Funding Email expansion-v2 -- specific-disclosure rate\n(consultative audit, NOT the primary outcome)",
            "% disclose_specific")
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.text(0.5, 0.01, "Stratified audit subset of n=150/arm; full human labeling\n"
                     "of the prereg's primary outcome is not yet done",
         ha="center", fontsize=8.5, color="#555", style="italic")
fig.savefig(OUT / "funding_email_expansion_consultative.png", dpi=200)
plt.close(fig)

# ---------- Figure 3: Eval Tampering -- pilot (primary) vs expansion (consultative) ----------
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)

n = 30
k_stated, k_artifact = 15, 21  # disclose (non-conceal-complement) counts, pilot
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
bar_with_ci(axes[0], ["Stated\n(n=30)", "Artifact\n(n=30)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Pilot (primary, human-labeled)", "% disclose (non-conceal)")

n = 150
k_stated, k_artifact = 52, 94
rates = [k_stated / n * 100, k_artifact / n * 100]
cis = [tuple(100 * c for c in wilson_ci(k_stated, n)), tuple(100 * c for c in wilson_ci(k_artifact, n))]
bar_with_ci(axes[1], ["Stated\n(n=150)", "Artifact\n(n=150)"], rates, cis, [STATED_C, ARTIFACT_C],
            "Expansion-v1 (consultative:\n4-model-rater / mechanical rule)", "")

fig.suptitle("Eval Tampering -- disclosure rate holds direction at 5x sample size",
             fontsize=12.5, fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "eval_tampering_pilot_vs_expansion.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Figure 4: Cross-environment sign flip ----------
fig, ax = plt.subplots(figsize=(8.2, 4.3))
envs = ["Funding Email\n(pilot, n=30/arm)", "Eval Tampering\n(pilot, n=30/arm)"]
deltas = [+6.7, -20.0]  # Artifact - Stated on disclose-rate, signed so + means Stated discloses more
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

print("Wrote figures to", OUT)
for p in sorted(OUT.glob("*.png")):
    print(" -", p.name, f"{p.stat().st_size/1024:.0f}KB")
