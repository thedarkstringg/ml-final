"""
K-Means clustering implemented from scratch using NumPy only (Lloyd's algorithm).
"""

from __future__ import annotations

import numpy as np


class KMeans:
    def __init__(
        self,
        n_clusters: int,
        max_iter: int = 300,
        tol: float = 1e-4,
        random_state: int | None = None,
    ) -> None:
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

        self.centroids_: np.ndarray | None = None
        self.labels_: np.ndarray | None = None
        self.inertia_: float | None = None
        self.n_iter_: int = 0

    def _init_centroids(self, X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
        """k-means++ initialization: spreads initial centroids out, which
        converges faster and more reliably than pure random initialization
        (the classic Lloyd's-algorithm failure mode is bad random starts
        landing multiple centroids in the same cluster)."""
        n_samples = X.shape[0]

        centroids = np.empty((self.n_clusters, X.shape[1]))
        first_idx = rng.randint(n_samples)
        centroids[0] = X[first_idx]

        for i in range(1, self.n_clusters):
            # distance from each point to its NEAREST already-chosen centroid
            dist_sq = np.min(
                np.sum((X[:, np.newaxis, :] - centroids[np.newaxis, :i, :]) ** 2, axis=2),
                axis=1,
            )
            # sample the next centroid with probability proportional to
            # squared distance -- points far from existing centroids are
            # more likely to be picked
            probs = dist_sq / dist_sq.sum() if dist_sq.sum() > 0 else np.ones(n_samples) / n_samples
            next_idx = rng.choice(n_samples, p=probs)
            centroids[i] = X[next_idx]

        return centroids

    def fit(self, X: np.ndarray) -> "KMeans":
        X = np.asarray(X, dtype=np.float64)
        n_samples = X.shape[0]

        if self.n_clusters > n_samples:
            raise ValueError(
                f"n_clusters={self.n_clusters} cannot exceed n_samples={n_samples}"
            )

        rng = np.random.RandomState(self.random_state)
        centroids = self._init_centroids(X, rng)

        labels = np.zeros(n_samples, dtype=int)

        for iteration in range(self.max_iter):
            # assignment step: assign each point to its nearest centroid
            distances = np.sum(
                (X[:, np.newaxis, :] - centroids[np.newaxis, :, :]) ** 2, axis=2
            )  # shape [n_samples, n_clusters]
            new_labels = np.argmin(distances, axis=1)

            # update step: recompute centroids as the mean of assigned points
            new_centroids = np.empty_like(centroids)
            for k in range(self.n_clusters):
                assigned = X[new_labels == k]
                if len(assigned) > 0:
                    new_centroids[k] = assigned.mean(axis=0)
                else:
                    # empty cluster: re-seed it at the point currently
                    # farthest from its assigned centroid, so no cluster
                    # silently disappears
                    point_dists = np.min(distances, axis=1)
                    farthest_idx = np.argmax(point_dists)
                    new_centroids[k] = X[farthest_idx]

            # convergence check: has the centroid movement dropped below tol?
            shift = np.sum((new_centroids - centroids) ** 2)
            centroids = new_centroids
            labels = new_labels
            self.n_iter_ = iteration + 1

            if shift < self.tol:
                break

        self.centroids_ = centroids
        self.labels_ = labels

        # inertia: sum of squared distances from each point to its assigned centroid
        final_distances = np.sum((X - centroids[labels]) ** 2, axis=1)
        self.inertia_ = float(final_distances.sum())

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Assign new points to the nearest already-fit centroid."""
        if self.centroids_ is None:
            raise RuntimeError("KMeans has not been fit yet.")

        X = np.asarray(X, dtype=np.float64)
        distances = np.sum(
            (X[:, np.newaxis, :] - self.centroids_[np.newaxis, :, :]) ** 2, axis=2
        )
        return np.argmin(distances, axis=1)

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.labels_

    def __repr__(self) -> str:
        fitted = self.centroids_ is not None
        inertia_str = f"{self.inertia_:.4f}" if self.inertia_ is not None else "None"
        return f"KMeans(n_clusters={self.n_clusters}, fitted={fitted}, inertia_={inertia_str})"
