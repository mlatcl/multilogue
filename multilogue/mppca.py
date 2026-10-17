"""Mixture of probabilistic PCA for soft phrase→topic geometry.

K-means initialises component means; EM updates responsibilities under
shared fixed topic noise ``sigma2`` (CIP-0017: topic σ² is fixed per run,
independent of lens-level σ²*). Soft responsibilities are the primary
return; harden helpers live elsewhere for LLM/report boundaries.

PPCA factor truncation matches :func:`multilogue.soft.fit_lens_ppca`
(eigenvalues above ``sigma2`` retained).
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from sklearn.cluster import KMeans

from .soft import log_likelihood_ppca

# Default topic noise floor for L2-normalised embedding spaces.
# Independent of lens σ²*; document changes in concept docs / CIP-0017.
DEFAULT_TOPIC_SIGMA2: float = 0.1


def _l2_normalize_rows(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(norms, eps, None)


def fit_weighted_ppca(
    X: np.ndarray,
    weights: np.ndarray,
    sigma2: float,
) -> dict:
    """PPCA Gaussian for one component under soft (or hard) weights.

    Mean is the responsibility-weighted mean. Covariance uses a weighted
    SVD of centred points (``sqrt(w_i) (x_i - μ)``); eigenvalues are
    ``s² / Σ w``. Factors with eigenvalue > ``sigma2`` are retained.
    """
    X = np.asarray(X, dtype=float)
    w = np.asarray(weights, dtype=float).ravel()
    if X.ndim != 2:
        raise ValueError(f"X must be 2-D, got shape {X.shape}")
    if w.shape[0] != X.shape[0]:
        raise ValueError("weights length must match X rows")
    if sigma2 <= 0:
        raise ValueError(f"sigma2 must be positive, got {sigma2}")

    w_sum = float(w.sum())
    d = X.shape[1]
    if w_sum <= 0:
        mu = np.zeros(d)
        return {
            "mu": mu,
            "U_q": np.zeros((d, 0)),
            "lambdas_q": np.zeros(0),
            "log_det": d * np.log(sigma2),
            "q": 0,
            "weight_sum": 0.0,
        }

    mu = (w[:, None] * X).sum(axis=0) / w_sum
    Xc = X - mu
    # Effective sample size for truncation / empty-component guard
    n_eff = float((w > 0).sum())
    if n_eff < 2:
        return {
            "mu": mu,
            "U_q": np.zeros((d, 0)),
            "lambdas_q": np.zeros(0),
            "log_det": d * np.log(sigma2),
            "q": 0,
            "weight_sum": w_sum,
        }

    sw = np.sqrt(np.clip(w, 0.0, None))
    Xw = sw[:, None] * Xc
    _, s, Vt = np.linalg.svd(Xw, full_matrices=False)
    lambdas = (s ** 2) / w_sum
    retain = lambdas > sigma2
    q = int(retain.sum())
    U_q = Vt[retain].T
    lambdas_q = lambdas[retain]
    log_det = float(np.sum(np.log(lambdas_q))) + (d - q) * float(np.log(sigma2))
    return {
        "mu": mu,
        "U_q": U_q,
        "lambdas_q": lambdas_q,
        "log_det": log_det,
        "q": q,
        "weight_sum": w_sum,
    }


def _softmax_rows(log_joint: np.ndarray) -> np.ndarray:
    shifted = log_joint - log_joint.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def mppca_fit(
    X: np.ndarray,
    k: int,
    *,
    sigma2: float = DEFAULT_TOPIC_SIGMA2,
    seed: int = 0,
    max_iter: int = 50,
    tol: float = 1e-5,
    n_init: int = 10,
    normalize_means: bool = True,
) -> dict[str, Any]:
    """Fit a mixture of PPCA components (k-means init, fixed shared σ²).

    Parameters
    ----------
    X :
        ``(n, d)`` phrase embeddings (typically already L2-normalised).
    k :
        Number of topic components.
    sigma2 :
        Shared topic noise floor (fixed for this run; CIP-0017).
    seed :
        K-means / reproducibility seed.
    max_iter :
        Maximum EM iterations after initialisation.
    tol :
        Stop when max absolute change in responsibilities falls below this.
    n_init :
        Passed to sklearn ``KMeans``.
    normalize_means :
        If True, L2-normalise returned ``means`` for cosine consumers
        (raw EM means remain in each component fit's ``mu``).

    Returns
    -------
    dict with keys
        ``responsibilities`` : ``(n, k)`` rows sum to 1
        ``means`` : ``(k, d)`` component means (normalised if requested)
        ``pi`` : ``(k,)`` mixing weights
        ``sigma2`` : topic σ² used
        ``n_iter`` : EM iterations performed
        ``component_fits`` : list of per-component PPCA dicts
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"X must be 2-D, got shape {X.shape}")
    n, d = X.shape
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if n < k:
        raise ValueError(f"need at least k={k} points, got n={n}")
    if sigma2 <= 0:
        raise ValueError(f"sigma2 must be positive, got {sigma2}")

    km = KMeans(n_clusters=k, random_state=seed, n_init=n_init)
    labels = km.fit_predict(X)
    R = np.zeros((n, k), dtype=float)
    R[np.arange(n), labels] = 1.0
    pi = R.mean(axis=0)

    component_fits: list[dict] = []
    n_iter = 0
    for n_iter in range(1, max_iter + 1):
        component_fits = [
            fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)
        ]
        log_lik = np.column_stack(
            [log_likelihood_ppca(X, fit, sigma2) for fit in component_fits]
        )
        # Empty components: zero prior mass → -inf joint
        log_pi = np.log(np.clip(pi, 1e-300, None))
        for j, fit in enumerate(component_fits):
            if fit.get("weight_sum", 0.0) <= 0:
                log_pi[j] = -np.inf
        log_joint = log_lik + log_pi[None, :]
        R_new = _softmax_rows(log_joint)
        pi = R_new.mean(axis=0)
        delta = float(np.max(np.abs(R_new - R)))
        R = R_new
        if delta < tol:
            break

    # Final M-step so returned fits match responsibilities
    component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
    means = np.vstack([fit["mu"] for fit in component_fits])
    if normalize_means:
        means = _l2_normalize_rows(means)

    return {
        "responsibilities": R,
        "means": means,
        "pi": pi,
        "sigma2": float(sigma2),
        "n_iter": int(n_iter),
        "component_fits": component_fits,
        "seed": int(seed),
        "k": int(k),
    }


def responsibilities_to_labels(responsibilities: np.ndarray) -> np.ndarray:
    """MAP (hard) topic labels from soft responsibilities — late view only."""
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    return np.argmax(R, axis=1).astype(int)
