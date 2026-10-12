"""Loading the Braatz Tennessee Eastman files and cutting them into windows.

Expected files in data/: d00.dat, d00_te.dat, dXX.dat, dXX_te.dat (XX = 01..21).
d00.dat is stored transposed (52 x 500) in the original release; this loader fixes that.
"""
from pathlib import Path
import numpy as np


def _load(path: Path) -> np.ndarray:
    x = np.loadtxt(path)
    if x.shape[0] == 52 and x.shape[1] != 52:
        x = x.T
    return x


def load_tep(data_dir: Path, faults, test_fault_start: int):
    """Return dicts {fault_id: array(samples, 52)} for train and test."""
    data_dir = Path(data_dir)
    train, test = {}, {}
    for f in [0] + list(faults):
        tag = f"d{f:02d}"
        train[f] = _load(data_dir / f"{tag}.dat")
        te = _load(data_dir / f"{tag}_te.dat")
        test[f] = te if f == 0 else te[test_fault_start:]
    return train, test


def windows(x: np.ndarray, size: int, stride: int) -> np.ndarray:
    idx = range(0, len(x) - size + 1, stride)
    return np.stack([x[i:i + size] for i in idx])


def build_splits(train, test, cfg, rng):
    """Classifier-train / calibration windows from training files (temporal split),
    test windows from *_te files, subsampled to cfg.windows_per_class."""
    Xtr, ytr, Xcal, ycal, Xte, yte = [], [], [], [], [], []
    for f, x in train.items():
        cut = int(len(x) * (1 - cfg.calib_fraction))
        w1 = windows(x[:cut], cfg.window, cfg.train_stride)
        w2 = windows(x[cut:], cfg.window, cfg.train_stride)
        Xtr.append(w1); ytr += [f] * len(w1)
        Xcal.append(w2); ycal += [f] * len(w2)
    for f, x in test.items():
        w = windows(x, cfg.window, cfg.test_stride)
        pick = rng.choice(len(w), size=min(cfg.windows_per_class, len(w)), replace=False)
        Xte.append(w[np.sort(pick)]); yte += [f] * len(pick)
    cat = lambda a: np.concatenate(a)
    return (cat(Xtr), np.array(ytr), cat(Xcal), np.array(ycal), cat(Xte), np.array(yte))


def inject_shift(Xw: np.ndarray, sd: np.ndarray, rng, n_vars=3, kind="bias", size=3.0):
    """Sensor-fault shift on a few variables: constant bias or linear drift (in units of
    the normal-operation standard deviation)."""
    X = Xw.copy()
    for i in range(len(X)):
        v = rng.choice(X.shape[2], size=n_vars, replace=False)
        if kind == "bias":
            X[i][:, v] += size * sd[v]
        else:
            ramp = np.linspace(0, size, X.shape[1])[:, None]
            X[i][:, v] += ramp * sd[v]
    return X


def make_synthetic(faults, n_train=480, n_test=800, seed=0):
    """Synthetic stand-in with the same shapes, for smoke tests only."""
    rng = np.random.default_rng(seed)
    base = rng.normal(size=(52, 52)) * 0.3
    def gen(n, f):
        x = rng.normal(size=(n, 52)) @ base + rng.normal(size=(n, 52))
        if f:
            vs = np.random.default_rng(f).choice(52, 4, replace=False)
            x[:, vs] += 2.5 + 0.2 * f
        return x
    train = {f: gen(500 if f == 0 else n_train, f) for f in [0] + list(faults)}
    test = {f: gen(n_test, f) for f in [0] + list(faults)}
    return train, test
