# backend/app/services/analytics/segmentation.py
"""
Customer Segmentation engine (K-Means with automatic k selection, or DBSCAN),
plus PCA for 2D visualization.

Pure function of (DataFrame, features, algorithm, k range) -> SegmentationFitResult.
Features are standardized (zero mean, unit variance) before clustering so
that no single feature dominates purely due to its scale.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


class SegmentationError(ValueError):
    """Raised when the requested segmentation cannot be computed."""


@dataclass
class ElbowPoint:
    k: int
    inertia: float
    silhouette: Optional[float]


@dataclass
class ClusterProfile:
    cluster: int
    name: str
    size: int
    share: float
    feature_means: dict


@dataclass
class PCAPoint:
    x: float
    y: float
    cluster: int


@dataclass
class SegmentationFitResult:
    algorithm: str
    n_clusters: Optional[int]
    silhouette: Optional[float]
    elbow: list[ElbowPoint] = field(default_factory=list)
    clusters: list[ClusterProfile] = field(default_factory=list)
    pca_explained_variance: list[float] = field(default_factory=list)
    pca_points: list[PCAPoint] = field(default_factory=list)
    centroids: dict = field(default_factory=dict)
    interpretation: str = ""


def _auto_name_cluster(feature_means: dict, global_means: dict) -> str:
    """
    Heuristic naming: describe the cluster by which features are most above/
    below the overall average, e.g. "High-value, high-frequency segment".
    """
    if not feature_means:
        return "Segment"

    deltas = []
    for feat, mean in feature_means.items():
        g = global_means.get(feat, 0.0)
        spread = abs(g) if abs(g) > 1e-9 else 1.0
        deltas.append((feat, (mean - g) / spread))

    deltas.sort(key=lambda t: abs(t[1]), reverse=True)
    top = deltas[:2]

    descriptors = []
    for feat, rel_delta in top:
        direction = "élevé" if rel_delta > 0.15 else ("faible" if rel_delta < -0.15 else None)
        if direction:
            descriptors.append(f"{feat} {direction}")

    if not descriptors:
        return "Segment moyen"
    return "Segment : " + ", ".join(descriptors)


def compute_segmentation(
    df: pd.DataFrame,
    features: list[str],
    algorithm: str = "kmeans",
    k_min: int = 2,
    k_max: int = 10,
) -> SegmentationFitResult:
    """Run K-Means (auto-k via elbow + silhouette) or DBSCAN, plus a 2D PCA projection."""
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise SegmentationError(f"Colonnes inconnues : {', '.join(missing)}")

    working = df[features].apply(pd.to_numeric, errors="coerce").dropna()
    if len(working) < max(k_min, 10):
        raise SegmentationError(
            "Pas assez d'observations valides pour la segmentation (minimum 10 requis)."
        )

    scaler = StandardScaler()
    scaled = scaler.fit_transform(working.values)

    if algorithm == "dbscan":
        labels, n_clusters, elbow, silhouette = _fit_dbscan(scaled)
    else:
        labels, n_clusters, elbow, silhouette = _fit_kmeans_auto_k(scaled, k_min, k_max)

    working = working.copy()
    working["_cluster"] = labels

    global_means = working[features].mean().to_dict()

    clusters: list[ClusterProfile] = []
    total = len(working)
    for cluster_id in sorted(working["_cluster"].unique()):
        subset = working[working["_cluster"] == cluster_id]
        feature_means = {f: float(subset[f].mean()) for f in features}
        name = "Bruit / non classé" if cluster_id == -1 else _auto_name_cluster(feature_means, global_means)
        clusters.append(
            ClusterProfile(
                cluster=int(cluster_id),
                name=name,
                size=len(subset),
                share=len(subset) / total,
                feature_means=feature_means,
            )
        )

    # PCA projection for 2D visualization.
    n_components = min(2, scaled.shape[1])
    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(scaled)
    if n_components == 1:
        coords = np.hstack([coords, np.zeros((coords.shape[0], 1))])

    pca_points = [
        PCAPoint(x=float(coords[i, 0]), y=float(coords[i, 1]), cluster=int(labels[i]))
        for i in range(len(labels))
    ]
    explained_variance = [float(v) for v in pca.explained_variance_ratio_]

    centroids: dict = {}
    if algorithm != "dbscan":
        # Centroids in original feature space (inverse-transform the scaled centroids).
        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42).fit(scaled)
        original_centroids = scaler.inverse_transform(km.cluster_centers_)
        centroids = {
            str(i): {f: float(v) for f, v in zip(features, original_centroids[i])}
            for i in range(n_clusters)
        }

    n_noise = int((labels == -1).sum()) if algorithm == "dbscan" else 0
    if algorithm == "dbscan":
        interpretation = (
            f"DBSCAN a identifié {n_clusters} segment(s) dense(s) "
            f"({n_noise} observation(s) considérée(s) comme bruit, soit {n_noise/total:.1%})."
        )
    else:
        sil_str = f"{silhouette:.3f}" if silhouette is not None else "N/A"
        interpretation = (
            f"K-Means a identifié {n_clusters} segment(s) client(s) optimal(aux) "
            f"(score de silhouette={sil_str}), sélectionné(s) automatiquement par la méthode du coude "
            f"combinée au score de silhouette. Le segment le plus important représente "
            f"{max(c.share for c in clusters):.1%} de la base."
        )

    return SegmentationFitResult(
        algorithm=algorithm,
        n_clusters=n_clusters,
        silhouette=silhouette,
        elbow=elbow,
        clusters=clusters,
        pca_explained_variance=explained_variance,
        pca_points=pca_points,
        centroids=centroids,
        interpretation=interpretation,
    )


def _fit_kmeans_auto_k(scaled: np.ndarray, k_min: int, k_max: int):
    """Try k in [k_min, k_max], score each by inertia (elbow) + silhouette, pick best silhouette."""
    n = scaled.shape[0]
    k_max = min(k_max, n - 1, 10)
    k_min = min(k_min, k_max)

    elbow: list[ElbowPoint] = []
    best_k, best_silhouette, best_labels = k_min, -1.0, None

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(scaled)
        inertia = float(km.inertia_)
        sil = float(silhouette_score(scaled, km.labels_)) if k > 1 and len(set(km.labels_)) > 1 else None
        elbow.append(ElbowPoint(k=k, inertia=inertia, silhouette=sil))
        if sil is not None and sil > best_silhouette:
            best_silhouette = sil
            best_k = k
            best_labels = km.labels_

    if best_labels is None:
        km = KMeans(n_clusters=k_min, n_init=10, random_state=42).fit(scaled)
        best_labels = km.labels_
        best_k = k_min
        best_silhouette = None

    return best_labels, best_k, elbow, (best_silhouette if best_silhouette != -1.0 else None)


def _fit_dbscan(scaled: np.ndarray):
    """DBSCAN with a simple heuristic eps (based on feature-space density); no k to select."""
    from sklearn.neighbors import NearestNeighbors

    n_neighbors = min(5, scaled.shape[0] - 1)
    neighbors = NearestNeighbors(n_neighbors=n_neighbors).fit(scaled)
    distances, _ = neighbors.kneighbors(scaled)
    eps = float(np.median(distances[:, -1])) or 0.5

    db = DBSCAN(eps=eps, min_samples=n_neighbors).fit(scaled)
    labels = db.labels_
    unique_clusters = sorted(set(labels) - {-1})
    n_clusters = len(unique_clusters)

    silhouette = None
    if n_clusters > 1:
        mask = labels != -1
        if mask.sum() > n_clusters:
            silhouette = float(silhouette_score(scaled[mask], labels[mask]))

    return labels, n_clusters, [], silhouette
