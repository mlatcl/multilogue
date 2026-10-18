"""Tests for soft-throughout MPPCA topic fit (CIP-0017)."""

import numpy as np
import pytest

from multilogue.mppca import (
    DEFAULT_TOPIC_SIGMA2,
    DEFAULT_TOPIC_SIGMA2_GRID,
    fit_weighted_ppca,
    mppca_fit,
    profile_topic_sigma2,
    responsibilities_to_labels,
)


def _planted_subspace_mixture(
    *,
    n_per: int = 40,
    d: int = 16,
    seed: int = 0,
    overlap: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Three elongated Gaussians in orthogonal 2-D subspaces of R^d.

    ``overlap`` shifts means toward the origin so components mix.
    """
    rng = np.random.default_rng(seed)
    means = np.zeros((3, d))
    means[0, 0] = 3.0 - overlap
    means[1, 2] = 3.0 - overlap
    means[2, 4] = 3.0 - overlap
    Xs = []
    labels = []
    for j in range(3):
        # elongate along two axes starting at 2*j
        axis_a, axis_b = 2 * j, 2 * j + 1
        cov = np.eye(d) * 0.05
        cov[axis_a, axis_a] = 0.8
        cov[axis_b, axis_b] = 0.5
        Xj = rng.multivariate_normal(means[j], cov, size=n_per)
        Xs.append(Xj)
        labels.append(np.full(n_per, j, dtype=int))
    X = np.vstack(Xs)
    y = np.concatenate(labels)
    # shuffle
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


def test_default_topic_sigma2_positive():
    assert DEFAULT_TOPIC_SIGMA2 > 0


def test_fit_weighted_ppca_matches_unweighted_mean():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(20, 5))
    w = np.ones(20)
    fit = fit_weighted_ppca(X, w, sigma2=0.1)
    np.testing.assert_allclose(fit["mu"], X.mean(axis=0), rtol=1e-10)


def test_mppca_responsibilities_row_stochastic():
    X, _ = _planted_subspace_mixture(seed=2)
    out = mppca_fit(X, k=3, sigma2=0.1, seed=2, max_iter=30)
    R = out["responsibilities"]
    assert R.shape == (X.shape[0], 3)
    assert np.all(R >= 0)
    np.testing.assert_allclose(R.sum(axis=1), 1.0, atol=1e-8)
    assert out["sigma2"] == pytest.approx(0.1)
    assert out["means"].shape == (3, X.shape[1])
    # L2-normalised means by default
    norms = np.linalg.norm(out["means"], axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-8)


def test_mppca_deterministic_given_seed():
    X, _ = _planted_subspace_mixture(seed=3)
    a = mppca_fit(X, k=3, sigma2=0.1, seed=3, max_iter=20)
    b = mppca_fit(X, k=3, sigma2=0.1, seed=3, max_iter=20)
    np.testing.assert_allclose(a["responsibilities"], b["responsibilities"], atol=1e-10)
    np.testing.assert_allclose(a["means"], b["means"], atol=1e-10)


def test_mppca_recovers_separated_components():
    X, y_true = _planted_subspace_mixture(seed=4, overlap=0.0)
    out = mppca_fit(X, k=3, sigma2=0.15, seed=4, max_iter=40)
    pred = responsibilities_to_labels(out["responsibilities"])
    # Hungarian-free: majority label per true class should be unique
    major = []
    for j in range(3):
        votes = pred[y_true == j]
        major.append(int(np.bincount(votes).argmax()))
    assert len(set(major)) == 3
    # Soft max responsibility high on average when well separated
    assert float(out["responsibilities"].max(axis=1).mean()) > 0.7


def test_mppca_softer_than_hard_under_overlap():
    """Under overlap, mean max-responsibility should be < 1 (soft mass shared)."""
    X, _ = _planted_subspace_mixture(seed=5, overlap=2.2, n_per=50)
    out = mppca_fit(X, k=3, sigma2=0.5, seed=5, max_iter=40)
    mean_max = float(out["responsibilities"].max(axis=1).mean())
    assert mean_max < 0.999
    assert mean_max > 1.0 / 3.0


def test_responsibilities_to_labels_argmax():
    R = np.array([[0.1, 0.7, 0.2], [0.9, 0.05, 0.05]])
    assert list(responsibilities_to_labels(R)) == [1, 0]


def test_responsibilities_to_labels_zero_row():
    R = np.array([[0.0, 0.0], [0.6, 0.4]])
    assert list(responsibilities_to_labels(R)) == [-1, 0]


def test_mppca_rejects_bad_sigma2():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(12, 4))
    with pytest.raises(ValueError, match="sigma2"):
        mppca_fit(X, k=2, sigma2=0.0, seed=0)


def _unit_sphere_topics(*, n_per: int = 20, d: int = 64, k: int = 5, seed: int = 0):
    """L2-normalised clusters mimicking embedding geometry."""
    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(k, d))
    centres /= np.linalg.norm(centres, axis=1, keepdims=True)
    Xs = []
    for j in range(k):
        noise = rng.normal(scale=0.08, size=(n_per, d))
        Xj = centres[j] + noise
        Xj /= np.linalg.norm(Xj, axis=1, keepdims=True)
        Xs.append(Xj)
    X = np.vstack(Xs)
    return X[rng.permutation(len(X))]


def test_default_sigma2_keeps_multiple_map_topics_on_sphere():
    """DEFAULT_TOPIC_SIGMA2 must not collapse MAP to one topic on unit sphere."""
    X = _unit_sphere_topics(seed=11)
    out = mppca_fit(X, k=5, seed=11, max_iter=40)  # uses DEFAULT
    labels = responsibilities_to_labels(out["responsibilities"])
    n_nonempty = int(np.bincount(labels, minlength=5).astype(bool).sum())
    assert n_nonempty >= 4
    assert out["sigma2"] == pytest.approx(DEFAULT_TOPIC_SIGMA2)


def test_high_sigma2_collapse_falls_back_to_kmeans_init():
    """When σ² is far above local eigenvalues, recover k-means init (not 1 MAP)."""
    X = _unit_sphere_topics(seed=12, n_per=25, k=6)
    out = mppca_fit(X, k=6, sigma2=1.0, seed=12, max_iter=40)
    assert out.get("collapsed") is True
    labels = responsibilities_to_labels(out["responsibilities"])
    n_nonempty = int(np.bincount(labels, minlength=6).astype(bool).sum())
    assert n_nonempty >= 5
    # Hard init responsibilities are one-hot
    assert np.allclose(out["responsibilities"].max(axis=1), 1.0)


def test_profile_topic_sigma2_avoids_collapse_and_prefers_soft():
    """Profile grid must reject collapsing floors and pick a soft viable σ²."""
    X = _unit_sphere_topics(seed=13, n_per=30, k=5, d=48)
    # Grid includes a known-collapsing high value and safer lower ones
    grid = [1e-3, 1e-2, 5e-2, 1.0]
    prof = profile_topic_sigma2(X, k=5, grid=grid, seed=13, max_iter=30)
    assert prof["selection"] == "softest_noncollapse"
    assert prof["sigma2"] < 1.0
    assert len(prof["curve"]) == len(grid)
    # Chosen fit must keep multiple MAP topics
    labels = responsibilities_to_labels(prof["fit"]["responsibilities"])
    assert int(np.bincount(labels, minlength=5).astype(bool).sum()) >= 3
    # And the chosen σ² should be the largest non-collapsing on the curve
    viable = [
        float(d["sigma2"])
        for d in prof["curve"]
        if (not d["collapsed"]) and int(d["n_map"]) >= 3 and float(d["max_mean_cos"]) <= 0.99
    ]
    assert prof["sigma2"] == max(viable)


def test_default_grid_nonempty():
    assert len(DEFAULT_TOPIC_SIGMA2_GRID) >= 5
    assert min(DEFAULT_TOPIC_SIGMA2_GRID) < DEFAULT_TOPIC_SIGMA2 < max(
        DEFAULT_TOPIC_SIGMA2_GRID
    )
