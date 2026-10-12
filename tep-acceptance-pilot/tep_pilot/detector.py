"""PCA monitoring on normal operation: Hotelling T2, SPE, and per-variable deviations."""
import numpy as np


class PCADetector:
    def __init__(self, var_explained=0.9, q=0.99):
        self.var_explained, self.q = var_explained, q

    def fit(self, x_normal: np.ndarray):
        self.mu = x_normal.mean(0)
        self.sd = x_normal.std(0) + 1e-8
        z = (x_normal - self.mu) / self.sd
        u, s, vt = np.linalg.svd(z, full_matrices=False)
        lam = s ** 2 / (len(z) - 1)
        k = int(np.searchsorted(np.cumsum(lam) / lam.sum(), self.var_explained) + 1)
        self.P, self.lam = vt[:k].T, lam[:k]
        t2, spe = self._stats(z)
        self.t2_lim, self.spe_lim = np.quantile(t2, self.q), np.quantile(spe, self.q)
        return self

    def z(self, x):
        return (x - self.mu) / self.sd

    def _stats(self, z):
        t = z @ self.P
        t2 = (t ** 2 / self.lam).sum(1)
        res = z - t @ self.P.T
        return t2, (res ** 2).sum(1)

    def window_report(self, w: np.ndarray, top_k: int):
        """Summary of one window: alarm flags and the top-k deviating variables."""
        z = self.z(w)
        t2, spe = self._stats(z)
        mean_dev = z.mean(0)
        order = np.argsort(-np.abs(mean_dev))[:top_k]
        return {
            "t2_ratio": float(t2.mean() / self.t2_lim),
            "spe_ratio": float(spe.mean() / self.spe_lim),
            "alarm": bool(t2.mean() > self.t2_lim or spe.mean() > self.spe_lim),
            "top_vars": [int(i) for i in order],
            "top_dev": [float(mean_dev[i]) for i in order],
        }
