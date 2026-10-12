"""Run the TEP acceptance-rule pilot end to end.

Examples
  python run_pilot.py --synthetic --llm mock               # smoke test, no data or API needed
  python run_pilot.py --llm ollama --model qwen2.5:7b       # real run, standard prompts
  python run_pilot.py --llm ollama --model qwen2.5:7b --masked   # contamination control
  python run_pilot.py --llm openai --model gpt-4o-mini
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from tep_pilot.config import Config, VARIABLES
from tep_pilot.data import load_tep, build_splits, inject_shift, make_synthetic
from tep_pilot.detector import PCADetector
from tep_pilot.checkers import window_features, SignatureModel, SplitConformal, grounded, accept
from tep_pilot.doer import Labels, LLMClient, diagnose
from tep_pilot.evaluate import curves, plot, point


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="use synthetic data (pipeline test only)")
    ap.add_argument("--llm", default="mock", choices=["mock", "ollama", "openai"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--masked", action="store_true")
    ap.add_argument("--windows-per-class", type=int, default=None)
    ap.add_argument("--faults", type=int, nargs="*", default=None)
    ap.add_argument("--tau", type=float, default=0.5, help="operating point reported in the summary")
    args = ap.parse_args()

    cfg = Config(llm=args.llm, masked=args.masked)
    if args.model: cfg.model = args.model
    if args.windows_per_class: cfg.windows_per_class = args.windows_per_class
    if args.faults: cfg.faults = args.faults
    rng = np.random.default_rng(cfg.seed)
    tag = ("synthetic_" if args.synthetic else "") + f"{cfg.llm}_{cfg.model.replace(':', '-')}_" + \
          ("masked" if cfg.masked else "standard")
    out = cfg.results_dir / tag
    out.mkdir(parents=True, exist_ok=True)

    # 1. Data and detector
    if args.synthetic:
        train, test = make_synthetic(cfg.faults, seed=cfg.seed)
    else:
        train, test = load_tep(cfg.data_dir, cfg.faults, cfg.test_fault_start)
    det = PCADetector().fit(train[0])
    Xtr, ytr, Xcal, ycal, Xte, yte = build_splits(train, test, cfg, rng)
    print(f"windows: train {len(ytr)}, calibration {len(ycal)}, test {len(yte)}")

    # 2. Checkers (independent of the LLM)
    sig = SignatureModel(cfg.seed).fit(window_features(Xtr, det), ytr)
    P_cal = sig.proba(window_features(Xcal, det))
    conf = SplitConformal().fit(P_cal, ycal, sig.index, cfg.alpha)
    P_te = sig.proba(window_features(Xte, det))
    sets_te = conf.sets(P_te, sig.classes)

    # 3. Doer
    labels = Labels([0] + list(cfg.faults), cfg.masked, cfg.seed)
    client = LLMClient(cfg.llm, cfg.model, cfg.temperature, cfg.results_dir / "llm_cache.jsonl")
    rows = []
    for i in tqdm(range(len(yte)), desc="diagnosing"):
        rep = det.window_report(Xte[i], cfg.top_k)
        d = diagnose(client, rep, labels, truth=int(yte[i]), rng=np.random.default_rng(cfg.seed + i))
        rows.append({
            "truth": int(yte[i]), "alarm": rep["alarm"], "top_vars": rep["top_vars"],
            **d,
            "grounded": grounded(d["llm_evidence"], rep["top_vars"]),
            "sig_proba": {int(c): float(p) for c, p in zip(sig.classes, P_te[i])},
            "clf_pred": int(sig.classes[P_te[i].argmax()]), "clf_maxp": float(P_te[i].max()),
            "conf_set": sets_te[i],
        })
    df = pd.DataFrame(rows)

    # 4. Conformal coverage, clean and under sensor shift
    cov = [{"condition": "clean", "coverage": np.mean([y in s for y, s in zip(yte, sets_te)]),
            "mean_set_size": np.mean([len(s) for s in sets_te])}]
    for kind in ("bias", "drift"):
        Xs = inject_shift(Xte, det.sd, np.random.default_rng(cfg.seed + 1), kind=kind)
        ss = conf.sets(sig.proba(window_features(Xs, det)), sig.classes)
        cov.append({"condition": f"sensor {kind} (3 sd, 3 variables)",
                    "coverage": np.mean([y in s for y, s in zip(yte, ss)]),
                    "mean_set_size": np.mean([len(s) for s in ss])})
    cov = pd.DataFrame(cov)

    # 5. Curves, operating point, per-fault breakdown
    cur = curves(df, cfg.max_set_size)
    plot(cur, out / "risk_coverage.png")
    llm_ok = (df.llm_fault == df.truth).values
    acc = np.array([accept(r, args.tau, cfg.max_set_size) for r in df.to_dict("records")])
    df["accepted"] = acc
    op = pd.DataFrame([
        {"method": "LLM always accepted", **point(df.llm_fault.notna().values, llm_ok, llm_ok)},
        {"method": "LLM self-check", **point(df.llm_selfcheck_confirm.values & df.llm_fault.notna().values, llm_ok, llm_ok)},
        {"method": f"LLM + acceptance rule (tau={args.tau})", **point(acc, llm_ok, llm_ok)},
    ])
    per_fault = df.assign(llm_correct=llm_ok).groupby("truth").agg(
        n=("truth", "size"), alarm_rate=("alarm", "mean"), llm_accuracy=("llm_correct", "mean"),
        grounded_rate=("grounded", "mean"), accept_rate=("accepted", "mean")).reset_index()

    # 6. Save
    save = df.copy()
    save["conf_set"] = save.conf_set.apply(sorted)
    save.drop(columns=["llm_raw"]).to_csv(out / "windows.csv", index=False)
    cur.to_csv(out / "curves.csv", index=False)
    cov.to_csv(out / "conformal_coverage.csv", index=False)
    per_fault.to_csv(out / "per_fault.csv", index=False)
    fmt = lambda d: d.to_markdown(index=False, floatfmt=".3f", intfmt="d")
    per_fault["truth"] = per_fault["truth"].astype(int); per_fault["n"] = per_fault["n"].astype(int)
    summary = f"""# TEP acceptance-rule pilot: {tag}

{"**SYNTHETIC DATA AND/OR MOCK LLM: numbers test the code only and must not be reported.**" if args.synthetic or cfg.llm == "mock" else ""}

- Faults: {cfg.faults} plus normal operation; {len(yte)} test windows of {cfg.window} samples
- LLM: {cfg.llm} / {cfg.model}; prompt mode: {"masked" if cfg.masked else "standard"}
- LLM diagnosis accuracy: {llm_ok.mean():.3f}; evidence fully grounded: {df.grounded.mean():.3f}
- Signature classifier accuracy: {(df.clf_pred == df.truth).mean():.3f}
- Conformal target coverage: {1 - cfg.alpha:.2f}

## Operating point
{fmt(op)}

## Conformal coverage under sensor shift
{fmt(cov)}

## Per fault
{fmt(per_fault)}

Figure: risk_coverage.png
"""
    (out / "summary.md").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
