"""Mixture of probabilistic PCA for soft phrase→topic geometry.

K-means initialises component means; EM updates responsibilities under
shared fixed topic noise ``sigma2`` (CIP-0017: topic σ² is fixed per run,
independent of lens-level σ²*). Soft responsibilities are the primary
return; harden helpers live elsewhere for LLM/report boundaries.

PPCA factor truncation matches :func:`multilogue.soft.fit_lens_ppca`
(eigenvalues above ``sigma2`` retained).
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np
from sklearn.cluster import KMeans

from .soft import log_likelihood_ppca

# Fallback single-value floor if profiling is skipped. Prefer
# :func:`profile_topic_sigma2` (CIP-0017: short profile grid, then fix).
# Independent of lens σ²*.
DEFAULT_TOPIC_SIGMA2: float = 0.01

# Log-spaced candidate floors for one-shot topic σ² profiling.
# Softest non-collapsing value on this grid is selected.
DEFAULT_TOPIC_SIGMA2_GRID: tuple[float, ...] = (
    1e-4,
    3e-4,
    1e-3,
    3e-3,
    1e-2,
    3e-2,
    5e-2,
    1e-1,
    3e-1,
    1.0,
)


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
    labels_init = km.fit_predict(X)
    R = np.zeros((n, k), dtype=float)
    R[np.arange(n), labels_init] = 1.0
    pi = R.mean(axis=0)
    R_init = R.copy()

    component_fits: list[dict] = []
    n_iter = 0
    collapsed = False
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

    # Guard: isotropic collapse (all q=0 + means coincide) leaves one MAP topic.
    # Fall back to k-means init hard responsibilities + member means.
    map_sizes = np.bincount(np.argmax(R, axis=1), minlength=k)
    if normalize_means and k >= 2:
        cos = means @ means.T
        np.fill_diagonal(cos, 0.0)
        max_mean_cos = float(cos.max()) if cos.size else 0.0
    else:
        max_mean_cos = 0.0
    if int((map_sizes > 0).sum()) <= 1 or max_mean_cos > 0.999:
        collapsed = True
        R = R_init
        pi = R.mean(axis=0)
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
        "collapsed": collapsed,
    }


def topic_fit_diagnostics(fit: dict[str, Any]) -> dict[str, float | int | bool]:
    """Summarise whether an MPPCA fit separated topics or collapsed."""
    R = np.asarray(fit["responsibilities"], dtype=float)
    means = np.asarray(fit["means"], dtype=float)
    k = int(fit.get("k", R.shape[1]))
    labels = np.argmax(R, axis=1)
    map_sizes = np.bincount(labels, minlength=k)
    n_map = int((map_sizes > 0).sum())
    if means.shape[0] >= 2:
        cos = means @ means.T
        np.fill_diagonal(cos, 0.0)
        max_mean_cos = float(cos.max()) if cos.size else 0.0
    else:
        max_mean_cos = 0.0
    # Shannon entropy of each responsibility row
    eps = 1e-12
    ent = -(R * np.log(R + eps)).sum(axis=1)
    q_vals = [int(f.get("q", 0)) for f in fit.get("component_fits", [])]
    collapsed = bool(fit.get("collapsed", False)) or n_map <= 1 or max_mean_cos > 0.999
    return {
        "n_map": n_map,
        "max_mean_cos": max_mean_cos,
        "mean_max_resp": float(R.max(axis=1).mean()),
        "mean_entropy": float(ent.mean()),
        "mean_q": float(np.mean(q_vals)) if q_vals else 0.0,
        "collapsed": collapsed,
        "sigma2": float(fit["sigma2"]),
    }


def profile_topic_sigma2(
    X: np.ndarray,
    k: int,
    *,
    grid: Optional[Sequence[float]] = None,
    seed: int = 0,
    max_iter: int = 50,
    tol: float = 1e-5,
    n_init: int = 10,
    normalize_means: bool = True,
    min_map_fraction: float = 0.5,
) -> dict[str, Any]:
    r"""Sweep topic σ² and pick the softest floor that does not collapse.

    CIP-0017: topic σ² is profiled once per analysis config, then held fixed
    (independent of lens σ²*). Among grid values whose fit keeps enough MAP
    topics and separated means, choose the **largest** σ² (softest / fewest
    factors) — that is the collapse-avoiding analogue of the lens σ²* band.

    Returns
    -------
    dict with ``sigma2``, ``fit`` (full :func:`mppca_fit` at the choice),
    ``curve`` (list of diagnostics per grid point), ``selection``.
    """
    grid_vals = list(grid) if grid is not None else list(DEFAULT_TOPIC_SIGMA2_GRID)
    if not grid_vals:
        raise ValueError("topic σ² grid must be non-empty")
    min_map = max(2, int(np.ceil(min_map_fraction * k)))

    curve: list[dict[str, float | int | bool]] = []
    fits: dict[float, dict[str, Any]] = {}
    for s2 in sorted(float(s) for s in grid_vals):
        fit = mppca_fit(
            X,
            k,
            sigma2=s2,
            seed=seed,
            max_iter=max_iter,
            tol=tol,
            n_init=n_init,
            normalize_means=normalize_means,
        )
        diag = topic_fit_diagnostics(fit)
        curve.append(diag)
        fits[s2] = fit

    viable = [
        d
        for d in curve
        if (not d["collapsed"])
        and int(d["n_map"]) >= min_map
        and float(d["max_mean_cos"]) <= 0.99
    ]
    if viable:
        # Softest non-collapsing: largest σ²
        best = max(viable, key=lambda d: float(d["sigma2"]))
        selection = "softest_noncollapse"
    else:
        # Least-bad: most MAP topics, then lowest mean cosine
        best = max(
            curve,
            key=lambda d: (int(d["n_map"]), -float(d["max_mean_cos"])),
        )
        selection = "fallback_least_collapsed"

    s2_star = float(best["sigma2"])
    return {
        "sigma2": s2_star,
        "fit": fits[s2_star],
        "curve": curve,
        "selection": selection,
        "min_map": min_map,
    }


def responsibilities_to_labels(
    responsibilities: np.ndarray,
    *,
    empty_label: int = -1,
) -> np.ndarray:
    """MAP (hard) topic labels from soft responsibilities.

    **Late view only** — for LLM labelling / lens-partition prompts and
    human tables. Soft responsibilities remain the primary stored state
    (CIP-0017).

    Rows that are all-zero or non-finite receive ``empty_label`` (default
    ``-1``) instead of a spurious argmax onto topic 0.
    """
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    finite = np.isfinite(R)
    R = np.where(finite, R, 0.0)
    row_mass = R.sum(axis=1)
    labels = np.argmax(R, axis=1).astype(int)
    labels[row_mass <= 0] = empty_label
    return labels


def example_phrases_for_soft_topics(
    phrases,
    responsibilities: np.ndarray,
    *,
    n_top: int = 12,
    n_sample: int = 6,
    seed: int = 0,
) -> list[dict]:
    """Top-mass exemplars per topic for LLM / report harden views.

    Ranks phrases by responsibility to each component, takes the top
    ``n_top``, then optionally samples ``n_sample`` further phrases from
    the remainder (deterministic under ``seed``). Empty components
    (near-zero column mass) return an empty example list.

    This is a **harden view** for labelling boundaries — not a change to
    the soft topic geometry.
    """
    from .text import sha

    phrases = list(phrases)
    R = np.asarray(responsibilities, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"responsibilities must be 2-D, got shape {R.shape}")
    if len(phrases) != R.shape[0]:
        raise ValueError(
            f"phrases length {len(phrases)} != responsibilities rows {R.shape[0]}"
        )
    n, k = R.shape
    rng = np.random.default_rng(seed)
    units: list[dict] = []
    for c in range(k):
        mass = R[:, c]
        if float(mass.sum()) <= 0:
            units.append({"cluster": c, "examples": [], "key": f"{c}|empty"})
            continue
        order = np.argsort(-mass, kind="mergesort")  # stable
        top_idx = order[: min(n_top, n)]
        examples = [phrases[i] for i in top_idx]
        rest_idx = order[n_top:]
        if n_sample > 0 and len(rest_idx) > 0:
            # Prefer phrases that still have some mass on this topic
            rest_mass = mass[rest_idx]
            eligible = rest_idx[rest_mass > 0]
            if len(eligible) > 0:
                take = min(n_sample, len(eligible))
                chosen = rng.choice(eligible, size=take, replace=False)
                # Stable order by descending mass among samples
                chosen = chosen[np.argsort(-mass[chosen], kind="mergesort")]
                examples.extend(phrases[i] for i in chosen)
        key = f"{c}|" + sha("|".join(str(p) for p in examples))[:10]
        units.append({"cluster": int(c), "examples": examples, "key": key})
    return units
