"""Metrics and the risk-coverage figure.

accepted-wrong rate = share of ACCEPTED diagnoses that are incorrect (our proxy for unsafe)
accept rate         = share of all windows where a diagnosis is accepted (the rest defer)
false rejection     = share of CORRECT LLM diagnoses that were deferred
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .checkers import accept


def point(acc: np.ndarray, correct: np.ndarray, llm_correct=None) -> dict:
    n_acc = acc.sum()
    out = {
        "accept_rate": acc.mean(),
        "accepted_wrong_rate": (~correct[acc]).mean() if n_acc else np.nan,
        "n_accepted": int(n_acc),
    }
    if llm_correct is not None:
        out["false_rejection"] = (~acc[llm_correct]).mean() if llm_correct.any() else np.nan
    return out


def curves(df: pd.DataFrame, max_set_size: int):
    y = df["truth"].values
    llm_ok = (df["llm_fault"] == df["truth"]).values
    clf_ok = (df["clf_pred"] == df["truth"]).values
    taus = np.linspace(0, 1, 41)
    rows = []
    for t in taus:
        rows.append({"method": "LLM alone (confidence >= t)", "t": t,
                     **point((df["llm_confidence"] >= t).values & df["llm_fault"].notna().values, llm_ok, llm_ok)})
        rows.append({"method": "Classifier alone (max prob >= t)", "t": t,
                     **point((df["clf_maxp"] >= t).values, clf_ok)})
        acc = np.array([accept(r, t, max_set_size) for r in df.to_dict("records")])
        rows.append({"method": "LLM + acceptance rule (signature prob >= t)", "t": t,
                     **point(acc, llm_ok, llm_ok)})
    sc = df["llm_selfcheck_confirm"].values & df["llm_fault"].notna().values
    rows.append({"method": "LLM self-check", "t": np.nan, **point(sc, llm_ok, llm_ok)})
    rows.append({"method": "LLM always accepted", "t": np.nan,
                 **point(df["llm_fault"].notna().values, llm_ok, llm_ok)})
    return pd.DataFrame(rows)


def plot(curve_df: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    styles = {"LLM alone (confidence >= t)": "#8a8a8a",
              "Classifier alone (max prob >= t)": "#c97b2a",
              "LLM + acceptance rule (signature prob >= t)": "#00509e"}
    for m, c in styles.items():
        d = curve_df[curve_df.method == m].dropna(subset=["accepted_wrong_rate"]).sort_values("accept_rate")
        ax.plot(d.accept_rate, d.accepted_wrong_rate, marker="o", ms=3, lw=1.6, color=c, label=m)
    for m, mk in [("LLM self-check", "s"), ("LLM always accepted", "^")]:
        d = curve_df[curve_df.method == m]
        ax.scatter(d.accept_rate, d.accepted_wrong_rate, marker=mk, s=50, color="black", label=m, zorder=3)
    ax.set_xlabel("Accept rate (share of windows not deferred)")
    ax.set_ylabel("Accepted-wrong rate")
    ax.set_xlim(0, 1.02); ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3); ax.legend(fontsize=7.5, frameon=False)
    ax.set_title("Safety-utility trade-off on TEP (lower-right is better)", fontsize=10)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)
