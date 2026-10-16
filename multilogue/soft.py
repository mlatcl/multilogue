"""Soft PPCA lens memberships and σ² selection by EMD stability.

Ports the Bayesian soft-mixture layer from ``pub_dialogue.address`` (Oct 2026).
Hard *k*-means and blind lens generation stay in :mod:`multilogue.cluster`;
this module consumes centroids and lens→cluster mappings.

EMD across lens runs requires the optional ``pot`` extra::

    pip install 'multilogue[distance]'
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Canonical rule: min mean-EMD among σ² with effective support in this
# open band × mean n_lenses. Without the band the unconstrained minimum is
# the near-uniform (degenerate) high-σ² end.
CANONICAL_SUPPORT_BAND: tuple[float, float] = (0.2, 0.6)


def _require_ot():
    try:
        import ot  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "The 'pot' library is required for EMD. Install: pip install pot "
            "(or pip install 'multilogue[distance]')"
        ) from exc
    return ot


def soft_mapping_from_hard(lens_of: dict) -> dict:
    """Convert ``{cluster_id: lens_name}`` to ``{lens: {\"cluster_ids\": [...]}}``."""
    by: dict[str, list[int]] = {}
    for c, name in lens_of.items():
        by.setdefault(str(name), []).append(int(c))
    return {L: {"cluster_ids": sorted(cs)} for L, cs in by.items()}


def fit_lens_ppca(member_centroids: np.ndarray, sigma2: float) -> dict:
    """Fit a PPCA Gaussian to one lens's member cluster centroids.

    Covariance Σ = W Wᵀ + σ² I with ARD-style truncation: factors with
    eigenvalue > σ² are retained. Returns ``mu``, ``U_q``, ``lambdas_q``,
    ``log_det``, ``q``.
    """
    m, d = member_centroids.shape
    mu = member_centroids.mean(axis=0)
    X = member_centroids - mu
    if m < 2:
        return {
            "mu": mu,
            "U_q": np.zeros((d, 0)),
            "lambdas_q": np.zeros(0),
            "log_det": d * np.log(sigma2),
            "q": 0,
        }
    _, s, Vt = np.linalg.svd(X, full_matrices=False)
    lambdas = (s ** 2) / m
    retain = lambdas > sigma2
    q = int(retain.sum())
    U_q = Vt[retain].T
    lambdas_q = lambdas[retain]
    log_det = float(np.sum(np.log(lambdas_q))) + (d - q) * float(np.log(sigma2))
    return {"mu": mu, "U_q": U_q, "lambdas_q": lambdas_q, "log_det": log_det, "q": q}


def log_likelihood_ppca(
    centroids: np.ndarray, lens_fit: dict, sigma2: float
) -> np.ndarray:
    """Log p(cluster | lens) under a PPCA Gaussian, up to a shared constant."""
    mu, U_q, lambdas_q, log_det = (
        lens_fit["mu"],
        lens_fit["U_q"],
        lens_fit["lambdas_q"],
        lens_fit["log_det"],
    )
    diff = centroids - mu
    if U_q.size > 0:
        v = diff @ U_q
        projected_sq = (v ** 2 / lambdas_q[None, :]).sum(axis=1)
        residual_sq = (diff ** 2).sum(axis=1) - (v ** 2).sum(axis=1)
    else:
        projected_sq = np.zeros(diff.shape[0])
        residual_sq = (diff ** 2).sum(axis=1)
    mahalanobis_sq = projected_sq + residual_sq / sigma2
    return -0.5 * mahalanobis_sq - 0.5 * log_det


def compute_mixture_weights(
    centroids: np.ndarray,
    lens_mapping: dict,
    sigma2: float,
    prior: str = "uniform",
) -> tuple[np.ndarray, list]:
    """Per-cluster mixture weights over lenses via PPCA Bayes posteriors.

    Parameters
    ----------
    centroids:
        ``(n_clusters, d)`` normalised cluster centroids.
    lens_mapping:
        ``{lens_name: {\"cluster_ids\": [...]}}``.
    sigma2:
        Shared noise variance.
    prior:
        ``'uniform'`` or ``'proportional'`` (to member count).

    Returns
    -------
    mixture_weights : ``(n_clusters, n_lenses)``, rows sum to 1
    lens_names : column order
    """
    lens_names = list(lens_mapping.keys())
    n_clusters = centroids.shape[0]
    log_lik = np.zeros((n_clusters, len(lens_names)))
    counts = np.zeros(len(lens_names), dtype=int)
    for j, name in enumerate(lens_names):
        entry = lens_mapping[name]
        raw_cids = entry["cluster_ids"] if isinstance(entry, dict) else entry
        cids = [c for c in raw_cids if 0 <= int(c) < n_clusters]
        counts[j] = len(cids)
        if not cids:
            log_lik[:, j] = -np.inf
            continue
        fit = fit_lens_ppca(centroids[cids], sigma2)
        log_lik[:, j] = log_likelihood_ppca(centroids, fit, sigma2)

    if prior == "proportional" and counts.sum() > 0:
        log_prior = np.log(counts / counts.sum())
    else:
        log_prior = np.zeros(len(lens_names))
    log_post = log_lik + log_prior[None, :]
    log_post -= log_post.max(axis=1, keepdims=True)
    post = np.exp(log_post)
    post /= post.sum(axis=1, keepdims=True)
    return post, lens_names


def _cosine_distance_matrix(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    X_n = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
    Y_n = Y / (np.linalg.norm(Y, axis=1, keepdims=True) + 1e-12)
    return 1.0 - X_n @ Y_n.T


def lens_means_from_mapping(centroids: np.ndarray, mapping: dict) -> np.ndarray:
    """Mean centroid per lens (rows follow ``mapping`` key order)."""
    n_clust = centroids.shape[0]
    names = list(mapping.keys())
    means = np.zeros((len(names), centroids.shape[1]))
    for i, name in enumerate(names):
        entry = mapping[name]
        raw = entry["cluster_ids"] if isinstance(entry, dict) else entry
        cids = [int(c) for c in raw if 0 <= int(c) < n_clust]
        if cids:
            means[i] = centroids[cids].mean(axis=0)
    return means


def pairwise_mean_emd(
    posteriors_runs: list, lens_means_runs: list
) -> dict:
    """Mean Earth Mover's Distance between runs' per-cluster mixture distributions."""
    ot = _require_ot()
    n_runs = len(posteriors_runs)
    n_clusters = posteriors_runs[0].shape[0]
    pair_rows = []
    all_emds: list[float] = []
    for i in range(n_runs):
        for j in range(i + 1, n_runs):
            cost = _cosine_distance_matrix(lens_means_runs[i], lens_means_runs[j])
            emds = []
            for c in range(n_clusters):
                a = np.maximum(posteriors_runs[i][c], 0.0)
                a = a / a.sum()
                b = np.maximum(posteriors_runs[j][c], 0.0)
                b = b / b.sum()
                emds.append(float(ot.emd2(a, b, cost)))
            pair_rows.append(
                {"run_a": i + 1, "run_b": j + 1, "mean_emd": float(np.mean(emds))}
            )
            all_emds.extend(emds)
    return {
        "overall_mean_emd": float(np.mean(all_emds)) if all_emds else float("nan"),
        "overall_median_emd": float(np.median(all_emds)) if all_emds else float("nan"),
        "pairs": pair_rows,
    }


def mean_n_lenses(mappings_list: Sequence[dict]) -> float:
    return float(np.mean([len(m) for m in mappings_list]))


def select_sigma2_in_band(
    stability_curve: pd.DataFrame,
    n_lenses: float,
    band: tuple[float, float] = CANONICAL_SUPPORT_BAND,
) -> float:
    """Min-EMD σ² among rows with ``band[0]·n < eff_support < band[1]·n``.

    Falls back to unconstrained minimum-EMD if no σ² lies in the band.
    """
    low, high = band[0] * n_lenses, band[1] * n_lenses
    inside = stability_curve[
        (stability_curve["mean_eff_support"] > low)
        & (stability_curve["mean_eff_support"] < high)
    ]
    pool = inside if not inside.empty else stability_curve
    return float(pool.loc[pool["mean_emd"].idxmin(), "sigma2"])


def select_sigma2_constrained(
    stability_curve: pd.DataFrame, n_lenses: float
) -> float:
    """Canonical rule: band (0.2, 0.6) × n_lenses."""
    return select_sigma2_in_band(stability_curve, n_lenses, CANONICAL_SUPPORT_BAND)


def _neighbour_on_grid(
    stability_curve: pd.DataFrame, n_lenses: float, step: int
) -> float:
    """σ² ``step`` grid points away from the constrained choice (clipped)."""
    grid = np.sort(stability_curve["sigma2"].to_numpy(dtype=float))
    canonical = select_sigma2_constrained(stability_curve, n_lenses)
    i = int(np.argmin(np.abs(grid - canonical)))
    return float(grid[min(max(i + step, 0), len(grid) - 1)])


def select_sigma2_one_step_harder(
    stability_curve: pd.DataFrame, n_lenses: float
) -> float:
    """Grid point just below constrained σ²* (sharper memberships)."""
    return _neighbour_on_grid(stability_curve, n_lenses, -1)


def select_sigma2_one_step_softer(
    stability_curve: pd.DataFrame, n_lenses: float
) -> float:
    """Grid point just above constrained σ²* (softer memberships)."""
    return _neighbour_on_grid(stability_curve, n_lenses, +1)


def select_sigma2_hard(
    stability_curve: pd.DataFrame, n_lenses: float = 0.0
) -> float:
    """Smallest σ² on the swept grid (near-hard assignment reference)."""
    return float(stability_curve["sigma2"].min())


SIGMA2_RULES: dict[str, Callable[[pd.DataFrame, float], float]] = {
    "constrained": select_sigma2_constrained,
    "one_step_harder": select_sigma2_one_step_harder,
    "one_step_softer": select_sigma2_one_step_softer,
    "hard": select_sigma2_hard,
}


def apply_sigma2_rule(
    rule: str, stability_curve: pd.DataFrame, n_lenses: float
) -> float:
    """Look up ``rule`` in :data:`SIGMA2_RULES` and evaluate it."""
    if rule not in SIGMA2_RULES:
        raise ValueError(
            f"Unknown sigma2_rule {rule!r}; expected one of {list(SIGMA2_RULES)}"
        )
    return SIGMA2_RULES[rule](stability_curve, n_lenses)


def sigma2_sweep_select(
    centroids: np.ndarray,
    mappings_list: list,
    sigma2_grid: Optional[np.ndarray] = None,
    kind: Optional[str] = None,
    output_folder: Optional[Path] = None,
    support_band: tuple[float, float] = CANONICAL_SUPPORT_BAND,
) -> dict:
    """Sweep σ² and select the stability-optimal value for PPCA soft memberships.

    For each σ², compute per-cluster mixture weights for each run, then mean
    pairwise EMD across runs. Select σ²* that minimises mean EMD subject to
    effective support in ``support_band × mean n_lenses``.
    """
    if sigma2_grid is None:
        sigma2_grid = np.logspace(-4, 2, 25)
    n_lens_avg = mean_n_lenses(mappings_list)
    low_cap, high_cap = support_band[0] * n_lens_avg, support_band[1] * n_lens_avg

    curve = []
    all_results_per_sigma = []
    for sigma2 in sigma2_grid:
        posteriors_runs, lens_means_runs = [], []
        diagnostics = []
        for mapping in mappings_list:
            post, _ = compute_mixture_weights(centroids, mapping, float(sigma2))
            means = lens_means_from_mapping(centroids, mapping)
            posteriors_runs.append(post)
            lens_means_runs.append(means)
            with np.errstate(divide="ignore", invalid="ignore"):
                lp = np.where(post > 0, np.log(post), 0.0)
            entropy_vec = -(post * lp).sum(axis=1)
            max_post = post.max(axis=1)
            diagnostics.append(
                {
                    "mean_eff_support": float(np.exp(entropy_vec).mean()),
                    "frac_hard_95": float((max_post > 0.95).mean()),
                    "frac_soft_50": float((max_post < 0.50).mean()),
                }
            )
        mean_eff = float(np.mean([d["mean_eff_support"] for d in diagnostics]))
        frac_hard = float(np.mean([d["frac_hard_95"] for d in diagnostics]))
        frac_soft = float(np.mean([d["frac_soft_50"] for d in diagnostics]))
        emd_info = pairwise_mean_emd(posteriors_runs, lens_means_runs)
        curve.append(
            {
                "sigma2": float(sigma2),
                "mean_eff_support": mean_eff,
                "frac_max_post_above_95": frac_hard,
                "frac_max_post_below_50": frac_soft,
                "mean_emd": emd_info["overall_mean_emd"],
                "median_emd": emd_info["overall_median_emd"],
            }
        )
        all_results_per_sigma.append((posteriors_runs, lens_means_runs))

    constrained = [
        (i, r)
        for i, r in enumerate(curve)
        if low_cap < r["mean_eff_support"] < high_cap
    ]
    if constrained:
        best_idx = min(constrained, key=lambda x: x[1]["mean_emd"])[0]
        selection = "constrained"
    else:
        best_idx = min(range(len(curve)), key=lambda i: curve[i]["mean_emd"])
        selection = "unconstrained (no σ² in meaningful-soft zone)"
        logger.warning(
            "No σ² gives eff_support in (%.1f, %.1f); using unconstrained min",
            low_cap,
            high_cap,
        )

    best = curve[best_idx]
    posteriors_runs, _ = all_results_per_sigma[best_idx]
    lens_names_runs = [list(m.keys()) for m in mappings_list]

    logger.info(
        "σ² sweep (%s): selected σ²=%g (%s), mean EMD=%.4f, eff_support=%.2f",
        kind or "unknown",
        best["sigma2"],
        selection,
        best["mean_emd"],
        best["mean_eff_support"],
    )

    if output_folder is not None and kind is not None:
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(curve).to_csv(
            output_folder / f"stability_curve_{kind}.csv", index=False
        )
        prefix = "benefit_" if kind == "benefit" else ""
        for i, post in enumerate(posteriors_runs):
            np.save(output_folder / f"{prefix}mixture_weights_run_{i + 1}.npy", post)
            (
                output_folder / f"{prefix}mixture_lens_names_run_{i + 1}.json"
            ).write_text(json.dumps(lens_names_runs[i]))
        np.save(output_folder / f"{prefix}mixture_weights.npy", posteriors_runs[0])
        (output_folder / f"{prefix}mixture_lens_names.json").write_text(
            json.dumps(lens_names_runs[0])
        )

    return {
        "curve": curve,
        "sigma2_best": best["sigma2"],
        "emd_best": best["mean_emd"],
        "eff_support_best": best["mean_eff_support"],
        "mixture_weights": posteriors_runs,
        "lens_names": lens_names_runs,
        "selection": selection,
        "low_cap": low_cap,
        "high_cap": high_cap,
    }
