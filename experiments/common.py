"""
Shared utilities for experiment scripts: output directories, dataset
loading (with graceful handling of the optional Credit Card CSV), and
small helpers reused across experiments/*.py.
"""

from __future__ import annotations

import json
import os
import sys

# Make the repo root importable regardless of how this script is invoked
# (e.g. `python experiments/scaling.py` vs `python -m experiments.run_all`
# vs running from a different working directory).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np

from src.utils.datasets import (
    load_breast_cancer_data,
    load_covertype_data,
    load_credit_card_fraud_data,
    load_mnist_binary_data,
)

FIGURES_DIR = "figures"
RESULTS_DIR = "results"


def ensure_output_dirs() -> None:
    os.makedirs(FIGURES_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)


def save_figure(fig, name: str) -> str:
    """Save a matplotlib figure to figures/<name>.png. Returns the path."""
    ensure_output_dirs()
    path = os.path.join(FIGURES_DIR, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def save_results_json(name: str, data: dict) -> str:
    """Save a results dict to results/<name>.json (converts numpy types
    to plain Python so json.dump doesn't choke on them)."""
    ensure_output_dirs()
    path = os.path.join(RESULTS_DIR, f"{name}.json")

    def _default(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=_default)
    return path


def get_available_datasets(credit_card_csv_path: str = "data/creditcard.csv") -> dict:
    """
    Load all datasets that are actually available right now, skipping any
    that fail (e.g. Credit Card Fraud if the CSV hasn't been downloaded yet,
    or MNIST/Covertype if there's no network access at the moment) with a
    warning instead of crashing the whole experiment run.

    Returns: {name: (X, y)} for every successfully loaded dataset.
    """
    datasets = {}

    loaders = [
        ("breast_cancer", lambda: load_breast_cancer_data()),
        ("credit_card_fraud", lambda: load_credit_card_fraud_data(credit_card_csv_path)),
        ("mnist_3_vs_8", lambda: load_mnist_binary_data(digit_a=3, digit_b=8, n_samples=6000)),
        ("covertype", lambda: load_covertype_data(n_samples=15000)),
    ]

    for expected_name, loader_fn in loaders:
        try:
            X, y, name = loader_fn()
            datasets[name] = (X, y)
            print(f"[OK]   Loaded {name}: X={X.shape}, y={y.shape}")
        except Exception as e:
            print(f"[SKIP] Could not load {expected_name}: {type(e).__name__}: {e}")

    if not datasets:
        raise RuntimeError(
            "No datasets could be loaded at all. At minimum, "
            "load_breast_cancer_data() should always work (no network/download "
            "needed) -- check your environment/imports."
        )

    return datasets


def is_binary(y: np.ndarray) -> bool:
    return len(np.unique(y)) == 2


def subsample_for_experiments(
    X: np.ndarray,
    y: np.ndarray,
    max_samples: int = 20000,
    random_state: int = 42,
    min_class_samples: int = 1,
) -> tuple:
    """
    Cap a dataset to at most max_samples rows, via stratified sampling
    (preserves class proportions -- critical for Credit Card Fraud, where
    the whole point is the severe imbalance).

    WHY THIS EXISTS: Experiment 1 (one model fit per dataset) is cheap
    enough to run on the full dataset -- e.g. the full 227,845-row Credit
    Card Fraud training set fits in under a minute. But Experiments 2-6
    fit MANY models (AdaBoost scaling alone fits 200 stumps; Random Forest
    scaling fits up to 200 UNPRUNED trees per sweep point, with no
    staged_predict shortcut available). At full Credit Card Fraud scale,
    that becomes hours of compute for a single experiment. Capping to
    max_samples=20000 keeps iteration times in the tens-of-seconds range
    while still preserving the severe class imbalance that makes this
    dataset interesting -- document this as a compute-tractability
    decision in the report, not a hidden shortcut.

    min_class_samples: guarantees at least this many samples per class,
    even if plain proportional stratification would give fewer. This
    matters a lot for CV metric stability: with Credit Card Fraud's
    ~0.17% minority rate, a naive proportional 5000-row subsample keeps
    only ~9 minority rows total, so each 5-fold CV test fold sees just
    1-2 minority examples -- F1 becomes essentially a coin flip on those
    1-2 points, producing enormous fold-to-fold variance that has nothing
    to do with actual model quality. Forcing e.g. min_class_samples=50
    fixes this at near-zero extra compute cost, since the minority class
    is such a tiny fraction of the total that even 50 forced rows barely
    changes the overall dataset size (majority class still dominates the
    row count and thus the compute cost).

    No-op (returns X, y unchanged) if X already has <= max_samples rows.
    """
    n_samples = X.shape[0]
    if n_samples <= max_samples:
        return X, y

    rng = np.random.RandomState(random_state)
    classes, counts = np.unique(y, return_counts=True)

    selected_indices = []
    for c, count in zip(classes, counts):
        class_indices = np.where(y == c)[0]
        # proportional allocation, but never below min_class_samples
        # (and never above what's actually available for that class)
        n_for_class = max(min_class_samples, int(round(max_samples * count / n_samples)))
        n_for_class = min(n_for_class, count)
        chosen = rng.choice(class_indices, size=n_for_class, replace=False)
        selected_indices.append(chosen)

    all_indices = np.concatenate(selected_indices)
    rng.shuffle(all_indices)

    return X[all_indices], y[all_indices]