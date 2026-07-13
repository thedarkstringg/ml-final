"""
Experiment 6: Bias-variance decomposition.

Select one balanced binary dataset (breast_cancer -- ~63/37 class split,
the most balanced of the 4 datasets, and small enough to make B=100
bootstrap replicates fully tractable). Generate B=100 bootstrap replicates
from the TRAINING data. For each replicate, train each model (single
DecisionTree, AdaBoost, RandomForest) and evaluate on a large FIXED test
set (the same held-out test set for every replicate -- only the training
data varies). Compute bias^2 and variance, then explain how boosting
(AdaBoost) reduces bias while bagging (RandomForest) reduces variance.

DEFINITIONS USED (0-1 loss classification decomposition, per Breiman
(1996) "Bias, Variance, and Arcing Classifiers", in the practical form
also used by Domingos (2000)):

For each test point x with true label y:
  - Collect the B models' predictions for x: {f_1(x), ..., f_B(x)}.
  - The "main prediction" f_main(x) is the MODE (most frequent prediction)
    across the B models -- this represents the "typical"/aggregate
    behavior of the learning algorithm on this dataset, stripped of the
    randomness from any single bootstrap draw.
  - bias(x) = 1 if f_main(x) != y, else 0.
    (i.e. is the algorithm's typical/aggregate behavior wrong?)
  - variance(x) = fraction of the B models whose prediction disagrees
    with f_main(x) (regardless of whether f_main(x) itself is correct).
    (i.e. how unstable are individual replicates around that typical
    behavior?)

Aggregate over the test set:
  - Bias^2 = mean(bias(x)) across all test points
  - Variance = mean(variance(x)) across all test points

This is a standard, defensible adaptation of the classical regression
bias-variance decomposition to 0-1 loss, and is what's typically meant by
"per Breiman (1996)" in a course-project context -- state this definition
explicitly in the report, since several minor variants exist in the
literature.

Run standalone:  python experiments/bias_variance.py
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats as scipy_stats
from sklearn.model_selection import train_test_split

from experiments.common import save_figure, save_results_json
from src.bagging.random_forest import RandomForestClassifier
from src.boosting.adaboost import AdaBoostClassifier
from src.trees.decision_tree import DecisionTree

B_REPLICATES = 100
N_ESTIMATORS = 100
TEST_SIZE = 0.3  # larger-than-usual held-out set, since the brief calls for a "large fixed test set"


def _mode_prediction(predictions_matrix: np.ndarray) -> np.ndarray:
    """predictions_matrix: shape [B, n_test]. Returns shape [n_test]:
    the mode (most frequent) prediction per test point across the B models."""
    mode_result = scipy_stats.mode(predictions_matrix, axis=0, keepdims=False)
    return mode_result.mode


def compute_bias_variance(predictions_matrix: np.ndarray, y_true: np.ndarray) -> dict:
    """
    predictions_matrix: shape [B, n_test] -- predictions_matrix[b, i] is
    model b's prediction for test point i.
    y_true: shape [n_test].
    """
    B = predictions_matrix.shape[0]
    main_pred = _mode_prediction(predictions_matrix)  # shape [n_test]

    bias_per_point = (main_pred != y_true).astype(float)  # shape [n_test]
    disagreement = (predictions_matrix != main_pred[np.newaxis, :])  # shape [B, n_test]
    variance_per_point = disagreement.mean(axis=0)  # shape [n_test]

    return {
        "bias_squared": float(bias_per_point.mean()),
        "variance": float(variance_per_point.mean()),
        "n_bootstrap_replicates": B,
    }


def run_experiment_6(
    breast_cancer_data: tuple,
    random_state: int = 42,
) -> dict:
    """
    breast_cancer_data: (X, y) for the chosen balanced binary dataset.
    """
    X, y = breast_cancer_data
    print(f"\n{'='*60}\nExperiment 6 -- bias-variance decomposition (breast_cancer)\n{'='*60}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=random_state, stratify=y
    )
    print(f"Train: {X_train.shape} (bootstrap source), Test (fixed, large): {X_test.shape}")

    n_train = X_train.shape[0]
    rng = np.random.RandomState(random_state)

    model_builders = {
        "single_tree": lambda: DecisionTree(max_depth=None, random_state=random_state),
        "adaboost": lambda: AdaBoostClassifier(n_estimators=N_ESTIMATORS, random_state=random_state),
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=N_ESTIMATORS, max_depth=None, random_state=random_state
        ),
    }

    predictions = {name: np.zeros((B_REPLICATES, X_test.shape[0]), dtype=y.dtype) for name in model_builders}

    for b in range(B_REPLICATES):
        boot_idx = rng.choice(n_train, size=n_train, replace=True)
        X_boot, y_boot = X_train[boot_idx], y_train[boot_idx]

        for name, builder in model_builders.items():
            model = builder()
            model.fit(X_boot, y_boot)
            predictions[name][b] = model.predict(X_test)

        if (b + 1) % 20 == 0:
            print(f"  ...{b + 1}/{B_REPLICATES} bootstrap replicates complete")

    results = {}
    for name, preds in predictions.items():
        bv = compute_bias_variance(preds, y_test)
        results[name] = bv
        print(f"  {name:15s}  bias^2={bv['bias_squared']:.4f}  variance={bv['variance']:.4f}")

    # --- interpretation check ---
    tree_bias, tree_var = results["single_tree"]["bias_squared"], results["single_tree"]["variance"]
    ada_bias, ada_var = results["adaboost"]["bias_squared"], results["adaboost"]["variance"]
    rf_bias, rf_var = results["random_forest"]["bias_squared"], results["random_forest"]["variance"]

    print(f"\nExpected pattern: AdaBoost should show lower bias than the single tree "
          f"(boosting reduces bias): {ada_bias:.4f} vs {tree_bias:.4f} "
          f"-- {'CONFIRMED' if ada_bias <= tree_bias else 'NOT observed on this run'}")
    print(f"Expected pattern: RandomForest should show lower variance than the single tree "
          f"(bagging reduces variance): {rf_var:.4f} vs {tree_var:.4f} "
          f"-- {'CONFIRMED' if rf_var <= tree_var else 'NOT observed on this run'}")

    # --- bar chart ---
    fig, ax = plt.subplots(figsize=(8, 5))
    model_names = list(results.keys())
    bias_values = [results[m]["bias_squared"] for m in model_names]
    var_values = [results[m]["variance"] for m in model_names]

    x_pos = np.arange(len(model_names))
    width = 0.35
    ax.bar(x_pos - width / 2, bias_values, width, label="Bias^2")
    ax.bar(x_pos + width / 2, var_values, width, label="Variance")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(model_names)
    ax.set_ylabel("Value")
    ax.set_title("Bias-Variance Decomposition: breast_cancer")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    save_figure(fig, "experiment_6_bias_variance_breast_cancer")
    plt.close(fig)

    save_results_json("experiment_6_bias_variance", results)
    return results


if __name__ == "__main__":
    from src.utils.datasets import load_breast_cancer_data
    X, y, _ = load_breast_cancer_data()
    run_experiment_6((X, y))