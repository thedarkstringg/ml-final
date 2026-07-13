"""
Unit tests for the from-scratch KMeans implementation.

Run with:  pytest tests/test_kmeans.py -v
"""

import numpy as np
import pytest
from sklearn.cluster import KMeans as SklearnKMeans
from sklearn.datasets import load_iris, make_blobs
from sklearn.metrics import adjusted_rand_score

from src.unsupervised.kmeans import KMeans


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def well_separated_blobs():
    X, y = make_blobs(n_samples=300, centers=4, cluster_std=0.5, random_state=42)
    return X, y


@pytest.fixture(scope="module")
def iris_data():
    return load_iris(return_X_y=True)


# ----------------------------------------------------------------------
# Basic correctness
# ----------------------------------------------------------------------
class TestBasicFit:
    def test_recovers_well_separated_clusters(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=4, random_state=42).fit(X)
        ari = adjusted_rand_score(y_true, km.labels_)
        assert ari > 0.9

    def test_output_shapes(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=4, random_state=42).fit(X)
        assert km.centroids_.shape == (4, X.shape[1])
        assert km.labels_.shape == (X.shape[0],)
        assert isinstance(km.inertia_, float)

    def test_reasonable_ari_on_iris(self, iris_data):
        X, y = iris_data
        km = KMeans(n_clusters=3, random_state=42).fit(X)
        ari = adjusted_rand_score(y, km.labels_)
        assert ari > 0.5


# ----------------------------------------------------------------------
# Agreement with sklearn
# ----------------------------------------------------------------------
class TestSklearnAgreement:
    def test_inertia_close_to_sklearn(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        my_km = KMeans(n_clusters=4, random_state=42).fit(X)
        skl_km = SklearnKMeans(n_clusters=4, random_state=42, n_init=10).fit(X)

        relative_diff = abs(my_km.inertia_ - skl_km.inertia_) / skl_km.inertia_
        assert relative_diff < 0.1  # within 10% -- different init strategies can converge to different local optima


# ----------------------------------------------------------------------
# predict / fit_predict
# ----------------------------------------------------------------------
class TestPredict:
    def test_predict_on_training_data_matches_labels(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=4, random_state=42).fit(X)
        preds = km.predict(X)
        assert np.array_equal(preds, km.labels_)

    def test_fit_predict_matches_fit_then_labels(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=4, random_state=42)
        labels = km.fit_predict(X)
        assert np.array_equal(labels, km.labels_)

    def test_predict_before_fit_raises(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=4)
        with pytest.raises(RuntimeError):
            km.predict(X)


# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------
class TestReproducibility:
    def test_same_seed_gives_identical_results(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km1 = KMeans(n_clusters=4, random_state=7).fit(X)
        km2 = KMeans(n_clusters=4, random_state=7).fit(X)
        assert np.array_equal(km1.labels_, km2.labels_)
        assert np.allclose(km1.centroids_, km2.centroids_)


# ----------------------------------------------------------------------
# Edge cases
# ----------------------------------------------------------------------
class TestEdgeCases:
    def test_n_clusters_one_centroid_is_overall_mean(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km = KMeans(n_clusters=1, random_state=42).fit(X)
        assert km.centroids_.shape == (1, X.shape[1])
        assert np.allclose(km.centroids_[0], X.mean(axis=0))

    def test_n_clusters_exceeds_n_samples_raises(self):
        X = np.random.RandomState(0).rand(5, 2)
        with pytest.raises(ValueError):
            KMeans(n_clusters=100).fit(X)

    def test_empty_cluster_does_not_produce_nan(self):
        """10 identical points + 1 far outlier, asked for 3 clusters --
        forces at least one cluster to start empty during iteration."""
        X = np.vstack([np.zeros((10, 2)), [[100.0, 100.0]]])
        km = KMeans(n_clusters=3, random_state=42).fit(X)
        assert not np.any(np.isnan(km.centroids_))

    def test_identical_points_all_assigned_same_cluster(self):
        X = np.ones((20, 3))
        km = KMeans(n_clusters=1, random_state=42).fit(X)
        assert km.inertia_ == pytest.approx(0.0, abs=1e-9)


# ----------------------------------------------------------------------
# repr
# ----------------------------------------------------------------------
class TestRepr:
    def test_repr_shows_fit_state(self, well_separated_blobs):
        X, y_true = well_separated_blobs
        km_unfit = KMeans(n_clusters=4)
        km_fit = KMeans(n_clusters=4, random_state=42).fit(X)

        assert "fitted=False" in repr(km_unfit)
        assert "fitted=True" in repr(km_fit)