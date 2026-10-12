"""The checkers, independent of the LLM.

Checker 1 (process consistency, pilot stand-in): a fault-signature classifier trained on
labelled simulated windows, plus an evidence-grounding test. In the full project this is
replaced by a P&ID-graph neural network process model.

Checker 2 (conformal set): split conformal prediction (LAC score) on the classifier's
probabilities, calibrated on held-out windows.
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier


def window_features(Xw: np.ndarray, detector) -> np.ndarray:
    """Per-variable mean and standard deviation of the standardised signal in each window."""
    Z = (Xw - detector.mu) / detector.sd
    return np.concatenate([Z.mean(1), Z.std(1)], axis=1)


class SignatureModel:
    def __init__(self, seed=0):
        self.clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                          class_weight="balanced", random_state=seed, n_jobs=-1)

    def fit(self, F, y):
        self.clf.fit(F, y)
        self.classes = self.clf.classes_
        self.index = {c: i for i, c in enumerate(self.classes)}
        return self

    def proba(self, F):
        return self.clf.predict_proba(F)


class SplitConformal:
    """LAC conformal sets: include every class whose score 1 - p is below the calibrated quantile."""

    def fit(self, P_cal, y_cal, index, alpha):
        scores = 1 - P_cal[np.arange(len(y_cal)), [index[c] for c in y_cal]]
        n = len(scores)
        level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        self.qhat = float(np.quantile(scores, level, method="higher"))
        return self

    def sets(self, P, classes):
        return [set(classes[(1 - p) <= self.qhat].tolist()) for p in P]


def grounded(evidence, top_vars) -> bool:
    """All cited variables must exist and be among the detector's top deviating variables."""
    return len(evidence) > 0 and all(e is not None and e in top_vars for e in evidence)


def accept(row, tau, max_set_size) -> bool:
    """The acceptance rule. Every check must pass, otherwise defer to the operator."""
    f = row["llm_fault"]
    if f is None:
        return False
    return (row["grounded"]
            and row["sig_proba"].get(f, 0.0) >= tau          # consistent with the fault signature
            and f in row["conf_set"]                          # inside the conformal set
            and len(row["conf_set"]) <= max_set_size)        # and the set is unambiguous
