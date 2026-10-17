"""Tests for soft-throughout MPPCA topic fit (CIP-0017)."""

import numpy as np
import pytest

from multilogue.mppca import (
    DEFAULT_TOPIC_SIGMA2,
    fit_weighted_ppca,
    mppca_fit,
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
