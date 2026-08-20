# backend/tests/test_segmentation.py
"""Unit tests for app.services.analytics.segmentation."""
import numpy as np
import pandas as pd
import pytest

from app.services.analytics.segmentation import SegmentationError, compute_segmentation


def _three_cluster_dataset(seed=3):
    rng = np.random.default_rng(seed)
    g1 = rng.normal([20, 50], [3, 5], (60, 2))
    g2 = rng.normal([80, 20], [3, 5], (60, 2))
    g3 = rng.normal([50, 90], [3, 5], (60, 2))
    data = np.vstack([g1, g2, g3])
    return pd.DataFrame(data, columns=["recency", "frequency"])


def test_kmeans_recovers_known_cluster_count():
    df = _three_cluster_dataset()
    result = compute_segmentation(df, features=["recency", "frequency"], algorithm="kmeans")

    assert result.n_clusters == 3
    assert result.silhouette > 0.5
    assert len(result.clusters) == 3
    assert sum(c.size for c in result.clusters) == 180
    assert abs(sum(c.share for c in result.clusters) - 1.0) < 1e-6


def test_kmeans_cluster_names_are_generated():
    df = _three_cluster_dataset()
    result = compute_segmentation(df, features=["recency", "frequency"], algorithm="kmeans")
    for c in result.clusters:
        assert c.name
        assert isinstance(c.name, str)


def test_pca_projection_present():
    df = _three_cluster_dataset()
    result = compute_segmentation(df, features=["recency", "frequency"], algorithm="kmeans")
    assert len(result.pca_points) == 180
    assert len(result.pca_explained_variance) == 2
    assert sum(result.pca_explained_variance) <= 1.0 + 1e-6


def test_elbow_data_covers_k_range():
    df = _three_cluster_dataset()
    result = compute_segmentation(
        df, features=["recency", "frequency"], algorithm="kmeans", k_min=2, k_max=6
    )
    ks = [e.k for e in result.elbow]
    assert ks == list(range(2, 7))
    # inertia should generally decrease as k increases
    inertias = [e.inertia for e in result.elbow]
    assert inertias[0] > inertias[-1]


def test_dbscan_runs_without_error():
    df = _three_cluster_dataset()
    result = compute_segmentation(df, features=["recency", "frequency"], algorithm="dbscan")
    assert result.algorithm == "dbscan"
    assert result.n_clusters is not None


def test_segmentation_unknown_feature_raises():
    df = _three_cluster_dataset()
    with pytest.raises(SegmentationError):
        compute_segmentation(df, features=["recency", "does_not_exist"])


def test_segmentation_too_few_rows_raises():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    with pytest.raises(SegmentationError):
        compute_segmentation(df, features=["a", "b"])
