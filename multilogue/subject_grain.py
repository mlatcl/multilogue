"""Subject-grain Assess helpers (CIP-0009 Layer A + lock artefact).

Question-agnostic soft-topic EDA: lock a catalogue for Address, merge/split
topics, build catalogues, and (via :mod:`multilogue.viz`) visualise the fit.
No LLM calls and no format-gap / study metrics here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

from .mppca import (
    DEFAULT_TOPIC_SIGMA2,
    DEFAULT_TOPIC_SIGMA2_GRID,
    fit_weighted_ppca,
    mppca_fit,
    profile_topic_sigma2,
    responsibilities_to_labels,
    example_phrases_for_soft_topics,
    topic_fit_diagnostics,
)
from .soft import log_likelihood_ppca
from .text import sha


def resolve_k_multiverse(
    primary_k: int,
    k_multiverse: str | Sequence[int] | None = "hold",
) -> list[int]:
    """Resolve Address multiverse (k) levels from a lock policy.

    Parameters
    ----------
    primary_k :
        Locked leaf / primary topic count (must be >= 1; Assess may start at 1).
    k_multiverse :
        ``\"hold\"`` / ``None`` → ``[primary_k]`` only;
        ``\"pm1\"`` → ``{k-1, k, k+1}`` clipped so every level is >= 1
        (and >= 2 when ``primary_k >= 2``, matching prior Address demos);
        an explicit sequence → sorted unique ints (each clipped to >= 1).
    """
    k = int(primary_k)
    if k < 1:
        raise ValueError(f"primary_k must be >= 1, got {primary_k}")
    floor = 1 if k == 1 else 2
    if k_multiverse is None or k_multiverse == "hold":
        return [k]
    if k_multiverse == "pm1":
        return sorted({max(floor, k - 1), k, k + 1})
    levels = sorted({max(floor, int(x)) for x in k_multiverse})
    if not levels:
        raise ValueError("k_multiverse sequence must be non-empty")
    return levels


def fit_fingerprint(
    responsibilities: np.ndarray | None = None,
    means: np.ndarray | None = None,
    *,
    labels: np.ndarray | None = None,
    decimals: int = 6,
) -> str:
    """Stable short hash of topic geometry for lock / checkpoint identity."""
    parts: list[str] = []
    if responsibilities is not None:
        R = np.round(np.asarray(responsibilities, dtype=float), decimals)
        parts.append("R:" + sha(R.tobytes()))
    if means is not None:
        M = np.round(np.asarray(means, dtype=float), decimals)
        parts.append("M:" + sha(M.tobytes()))
    if labels is not None:
        lab = np.asarray(labels, dtype=int)
        parts.append("L:" + sha(lab.tobytes()))
    if not parts:
        raise ValueError("need responsibilities, means, and/or labels")
    return sha("|".join(parts))[:16]


def lock_subject_grain(
    *,
    primary_k: int,
    responsibilities: np.ndarray | None = None,
    means: np.ndarray | None = None,
    labels: np.ndarray | None = None,
    history: Optional[Sequence[dict[str, Any]]] = None,
    k_multiverse: str | Sequence[int] | None = "hold",
    sigma2: float | None = None,
    diagnostics: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the locked subject-grain artefact for Address / run manifests.

    Does **not** choose *k* by maximising a study metric. Call after the
    analyst accepts the catalogue (Assess); Address reads ``primary_k`` and
    ``k_multiverse`` only.
    """
    k = int(primary_k)
    if k < 1:
        raise ValueError(f"primary_k must be >= 1, got {primary_k}")
    levels = resolve_k_multiverse(k, k_multiverse)
    fp = fit_fingerprint(
        responsibilities, means, labels=labels
    ) if (
        responsibilities is not None or means is not None or labels is not None
    ) else None
    lock: dict[str, Any] = {
        "primary_k": k,
        "k_multiverse": levels,
        "k_multiverse_policy": (
            k_multiverse
            if isinstance(k_multiverse, str) or k_multiverse is None
            else "explicit"
        ),
        "fit_fingerprint": fp,
        "history": list(history) if history else [],
    }
    if sigma2 is not None:
        lock["sigma2"] = float(sigma2)
    if responsibilities is not None:
        R = np.asarray(responsibilities, dtype=float)
        lock["n_phrases"] = int(R.shape[0])
        lock["n_topics"] = int(R.shape[1])
    elif labels is not None:
        lab = np.asarray(labels)
        lock["n_phrases"] = int(lab.shape[0])
        lock["n_topics"] = k
    if diagnostics is not None:
        lock["diagnostics"] = dict(diagnostics)
    if extra:
        lock.update(extra)
    return lock


def _softmax_rows(log_joint: np.ndarray) -> np.ndarray:
    shifted = log_joint - log_joint.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.clip(exp.sum(axis=1, keepdims=True), 1e-300, None)


def _fit_from_responsibilities(
    X: np.ndarray,
    R: np.ndarray,
    sigma2: float,
    *,
    seed: int = 0,
    max_iter: int = 30,
    tol: float = 1e-5,
    normalize_means: bool = True,
) -> dict[str, Any]:
    """Run EM M-steps / E-steps starting from given responsibilities."""
    from .mppca import _l2_normalize_rows

    X = np.asarray(X, dtype=float)
    R = np.asarray(R, dtype=float)
    n, k = R.shape
    pi = R.mean(axis=0)
    n_iter = 0
    max_iter = max(0, int(max_iter))
    if max_iter == 0:
        component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
        means = np.vstack([fit["mu"] for fit in component_fits])
        if normalize_means:
            means = _l2_normalize_rows(means)
        return {
            "responsibilities": R,
            "means": means,
            "pi": pi,
            "sigma2": float(sigma2),
            "n_iter": 0,
            "component_fits": component_fits,
            "seed": int(seed),
            "k": int(k),
            "collapsed": bool(
                topic_fit_diagnostics(
                    {
                        "responsibilities": R,
                        "means": means,
                        "sigma2": sigma2,
                        "k": k,
                        "component_fits": component_fits,
                    }
                )["collapsed"]
            ),
        }
    for n_iter in range(1, max_iter + 1):
        component_fits = [fit_weighted_ppca(X, R[:, j], sigma2) for j in range(k)]
        log_lik = np.column_stack(
            [log_likelihood_ppca(X, fit, sigma2) for fit in component_fits]
        )
        log_pi = np.log(np.clip(pi, 1e-300, None))
        for j, fit in enumerate(component_fits):
            if fit.get("weight_sum", 0.0) <= 0:
                log_pi[j] = -np.inf
        R_new = _softmax_rows(log_lik + log_pi[None, :])
        pi = R_new.mean(axis=0)
        delta = float(np.max(np.abs(R_new - R)))
        R = R_new
        if delta < tol:
            break
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
        "collapsed": bool(topic_fit_diagnostics(
            {"responsibilities": R, "means": means, "sigma2": sigma2, "k": k,
             "component_fits": component_fits}
        )["collapsed"]),
    }


def initial_assess_fit(
    X: np.ndarray,
    *,
    k: int = 1,
    sigma2_mode: str = "profile",
    sigma2: float | None = None,
    seed: int = 0,
    max_iter: int = 50,
    n_init: int = 10,
) -> dict[str, Any]:
    """Fit the Assess entry mixture (CIP-000A: default ``k=1``).

    Parameters
    ----------
    sigma2_mode :
        ``\"profile\"`` — CIP-0017 softest non-collapse grid (ignores ``sigma2``
        unless profiling is skipped for ``k`` edge cases).
        ``\"fixed\"`` — use ``sigma2`` or :data:`DEFAULT_TOPIC_SIGMA2`.
    """
    X = np.asarray(X, float)
    k = int(k)
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    mode = str(sigma2_mode or "profile").strip().lower()
    if mode not in {"profile", "fixed"}:
        raise ValueError(f"sigma2_mode must be 'profile' or 'fixed', got {sigma2_mode!r}")
    if mode == "fixed":
        s2 = float(sigma2) if sigma2 is not None else float(DEFAULT_TOPIC_SIGMA2)
        fit = mppca_fit(
            X, k, sigma2=s2, seed=seed, max_iter=max_iter, n_init=n_init
        )
        fit["sigma2_selection"] = {"selection": "fixed", "curve": []}
        return fit
    prof = profile_topic_sigma2(
        X, k, seed=seed, max_iter=max_iter, n_init=n_init
    )
    fit = prof["fit"]
    fit["sigma2_selection"] = {
        "selection": prof["selection"],
        "curve": prof["curve"],
        "min_map": prof.get("min_map"),
    }
    return fit


def profile_sigma2_holding_responsibilities(
    X: np.ndarray,
    R: np.ndarray,
    *,
    grid: Sequence[float] | None = None,
    seed: int = 0,
    max_iter: int = 0,
) -> dict[str, Any]:
    """CIP-0017-style σ² pick **without redistributing** soft assignments.

    Default ``max_iter=0``: for each grid value, only re-fit component geometry
    (M-step) under the *current* ``R``. Softest non-collapsing σ² wins, then the
    returned fit keeps that same ``R``. Full EM after Accept was collapsing one
    child of a balanced split on real embeddings — do not reintroduce that here.
    """
    X = np.asarray(X, float)
    R0 = np.asarray(R, float)
    if R0.ndim != 2 or R0.shape[0] != X.shape[0]:
        raise ValueError("R must be (n, k) aligned with X")
    k = int(R0.shape[1])
    n = int(R0.shape[0])
    grid_vals = list(grid) if grid is not None else list(DEFAULT_TOPIC_SIGMA2_GRID)
    min_map = 1 if k == 1 else max(2, int(np.ceil(0.5 * k)))
    # Reject floors that leave a near-empty MAP bag (when EM is allowed).
    min_map_count = 1 if k == 1 else max(2, int(np.ceil(0.05 * n)))
    score_iters = max(0, int(max_iter))
    curve: list[dict[str, Any]] = []
    fits: dict[float, dict[str, Any]] = {}
    for s2 in sorted(float(s) for s in grid_vals):
        fit = _fit_from_responsibilities(
            X, R0.copy(), s2, seed=seed, max_iter=score_iters
        )
        diag = topic_fit_diagnostics(fit)
        map_sizes = np.bincount(
            np.argmax(fit["responsibilities"], axis=1), minlength=k
        )
        diag["min_map_count"] = int(map_sizes.min()) if k else 0
        curve.append(diag)
        fits[s2] = fit
    viable = [
        d
        for d in curve
        if (not d["collapsed"])
        and int(d["n_map"]) >= min_map
        and int(d.get("min_map_count", 0)) >= min_map_count
        and float(d["max_mean_cos"]) <= 0.99
    ]
    if viable:
        best = max(viable, key=lambda d: float(d["sigma2"]))
        selection = "softest_noncollapse_held_R"
    else:
        best = max(
            curve,
            key=lambda d: (
                int(d["n_map"]),
                int(d.get("min_map_count", 0)),
                -float(d["max_mean_cos"]),
            ),
        )
        selection = "fallback_least_collapsed_held_R"
    s2_star = float(best["sigma2"])
    # Always return geometry under the *original* R at the chosen floor.
    out = _fit_from_responsibilities(
        X, R0.copy(), s2_star, seed=seed, max_iter=0
    )
    return {
        "sigma2": s2_star,
        "fit": out,
        "curve": curve,
        "selection": selection,
        "min_map": min_map,
    }


def propose_merge(
    X: np.ndarray,
    fit: dict[str, Any],
    topic_ids: Sequence[int],
    *,
    refit: bool = True,
    seed: int = 0,
    max_iter: int = 30,
) -> dict[str, Any]:
    """Merge soft mass of ``topic_ids`` into one leaf; return updated fit.

    Does **not** call an LLM. The merged leaf is marked dirty; unmerged
    topics keep their content under remapped indices (not dirty).
    """
    ids = sorted({int(i) for i in topic_ids})
    R = np.asarray(fit["responsibilities"], dtype=float)
    k = R.shape[1]
    if len(ids) < 2:
        raise ValueError("propose_merge needs at least two topic ids")
    if ids[0] < 0 or ids[-1] >= k:
        raise ValueError(f"topic ids {ids} out of range for k={k}")
    keep = [j for j in range(k) if j not in ids]
    merged = R[:, ids].sum(axis=1, keepdims=True)
    R_new = np.hstack([R[:, keep], merged]) if keep else merged
    R_new = R_new / np.clip(R_new.sum(axis=1, keepdims=True), 1e-12, None)
    sigma2 = float(fit["sigma2"])
    if refit:
        new_fit = _fit_from_responsibilities(
            X, R_new, sigma2, seed=seed, max_iter=max_iter
        )
    else:
        new_fit = _fit_from_responsibilities(
            X, R_new, sigma2, seed=seed, max_iter=1, tol=0.0
        )
    new_k = int(new_fit["k"])
    # Remap: kept topics → 0..len(keep)-1; merged → new_k-1
    old_to_new = {old: new for new, old in enumerate(keep)}
    merged_id = new_k - 1
    history_entry = {
        "action": "merge",
        "topics": ids,
        "merged_into": merged_id,
        "old_to_new": {str(a): b for a, b in old_to_new.items()},
    }
    return {
        "fit": new_fit,
        "dirty": [merged_id],
        "history_entry": history_entry,
        "old_to_new": old_to_new,
    }


def propose_split(
    X: np.ndarray,
    fit: dict[str, Any],
    topic_id: int,
    *,
    n_children: int = 2,
    seed: int = 0,
    mass_threshold: float = 0.05,
    max_iter: int = 40,
) -> dict[str, Any]:
    """Split one topic via a local mixture of PPCA on its soft mass.

    Geometry for all points: child responsibilities are the parent mass
    times local posterior under the child PPCA components. Does **not**
    call an LLM; both children are marked dirty.
    """
    if n_children < 2:
        raise ValueError(f"n_children must be >= 2, got {n_children}")
    R = np.asarray(fit["responsibilities"], dtype=float)
    X = np.asarray(X, dtype=float)
    i = int(topic_id)
    k = R.shape[1]
    if i < 0 or i >= k:
        raise ValueError(f"topic_id {i} out of range for k={k}")
    mass = R[:, i]
    mask = mass >= float(mass_threshold)
    if int(mask.sum()) < n_children:
        # Take top-mass points so local fit is feasible
        order = np.argsort(-mass)
        take = max(n_children, min(len(order), max(n_children * 5, n_children)))
        mask = np.zeros(len(mass), dtype=bool)
        mask[order[:take]] = True
    X_sub = X[mask]
    if X_sub.shape[0] < n_children:
        raise ValueError(
            f"not enough mass on topic {i} to split into {n_children} "
            f"(got {X_sub.shape[0]} points)"
        )
    sigma2 = float(fit["sigma2"])
    parent_cf = None
    cfs = fit.get("component_fits") or []
    if 0 <= i < len(cfs):
        parent_cf = deepcopy(cfs[i])
    local = mppca_fit(
        X_sub,
        n_children,
        sigma2=sigma2,
        seed=seed,
        max_iter=max_iter,
    )
    # Soft assignment of *all* points under local children
    log_lik = np.column_stack(
        [log_likelihood_ppca(X, cf, sigma2) for cf in local["component_fits"]]
    )
    log_pi = np.log(np.clip(local["pi"], 1e-300, None))
    r_local = _softmax_rows(log_lik + log_pi[None, :])
    child_cols = mass[:, None] * r_local
    # Largest soft mass first → lower topic index / catalogue top / default focus
    child_order = np.argsort(-child_cols.sum(axis=0))
    child_cols = child_cols[:, child_order]
    local = deepcopy(local)
    local["component_fits"] = [
        local["component_fits"][int(j)] for j in child_order
    ]
    local["pi"] = np.asarray(local["pi"], float)[child_order]
    if "means" in local:
        local["means"] = np.asarray(local["means"], float)[child_order]
    if "responsibilities" in local:
        local["responsibilities"] = np.asarray(
            local["responsibilities"], float
        )[:, child_order]
    parts = []
    if i > 0:
        parts.append(R[:, :i])
    parts.append(child_cols)
    if i + 1 < k:
        parts.append(R[:, i + 1 :])
    R_new = np.hstack(parts)
    R_new = R_new / np.clip(R_new.sum(axis=1, keepdims=True), 1e-12, None)
    new_fit = _fit_from_responsibilities(
        X, R_new, sigma2, seed=seed, max_iter=max_iter
    )
    # EM can nudge masses — re-sort child columns so largest stays first
    R_f = np.asarray(new_fit["responsibilities"], float)
    child_slice = R_f[:, i : i + n_children]
    post_order = np.argsort(-child_slice.sum(axis=0))
    if not np.array_equal(post_order, np.arange(n_children)):
        R_f[:, i : i + n_children] = child_slice[:, post_order]
        new_fit["responsibilities"] = R_f
        cfs = list(new_fit.get("component_fits") or [])
        if len(cfs) >= i + n_children:
            block = [cfs[i + int(j)] for j in post_order]
            for t, cf in enumerate(block):
                cfs[i + t] = cf
            new_fit["component_fits"] = cfs
        if "means" in new_fit and new_fit["means"] is not None:
            means = np.asarray(new_fit["means"], float)
            means[i : i + n_children] = means[i : i + n_children][post_order]
            new_fit["means"] = means
        if "pi" in new_fit and new_fit["pi"] is not None:
            pi = np.asarray(new_fit["pi"], float)
            pi[i : i + n_children] = pi[i : i + n_children][post_order]
            new_fit["pi"] = pi
        child_cols = child_cols[:, post_order]
        local["component_fits"] = [
            local["component_fits"][int(j)] for j in post_order
        ]
        local["pi"] = np.asarray(local["pi"], float)[post_order]
        if "means" in local:
            local["means"] = np.asarray(local["means"], float)[post_order]
        if "responsibilities" in local:
            local["responsibilities"] = np.asarray(
                local["responsibilities"], float
            )[:, post_order]
        child_order = child_order[post_order]
    child_ids = list(range(i, i + n_children))
    child_pi = np.asarray(local.get("pi"), float).ravel()
    kl = 0.0
    if parent_cf is not None:
        kl = parent_split_kl(
            X,
            mass,
            parent_cf,
            local["component_fits"],
            child_pi,
            sigma2,
        )
    history_entry = {
        "action": "split",
        "topic": i,
        "children": child_ids,
        "n_children": n_children,
        "child_order_by_mass": [int(j) for j in child_order],
        "kl": float(kl),
    }
    return {
        "fit": new_fit,
        "dirty": child_ids,
        "history_entry": history_entry,
        "local_fit": local,
        "parent_id": i,
        "parent_mass": mass.copy(),
        "parent_component_fit": parent_cf,
        "child_responsibilities": child_cols,
        "kl": float(kl),
    }


def topic_catalogue(
    phrases: Sequence[Any] | pd.DataFrame,
    responsibilities: np.ndarray,
    *,
    labels: Optional[Sequence[str]] = None,
    dirty: Optional[Sequence[int]] = None,
    phrase_col: str = "phrase",
    n_examples: int = 4,
    seed: int = 0,
    parent_labels: Optional[Sequence[str | None] | dict[int, str]] = None,
    proposed: Optional[Sequence[int]] = None,
) -> pd.DataFrame:
    """Semantic catalogue table for soft topics (exemplars + dirty flags).

    Deterministic given ``seed`` / exemplars. Does not call an LLM — optional
    ``labels`` are pass-through reading aids (may be stale placeholders).

    ``parent_labels`` records the pre-split LLM name for topics born from a
    split (so the catalogue shows original label *and* the proposed children).
    ``proposed`` marks topics that are still under a pending split proposal.
    """
    R = np.asarray(responsibilities, dtype=float)
    if isinstance(phrases, pd.DataFrame):
        if phrase_col not in phrases.columns:
            raise ValueError(f"phrases DataFrame needs column {phrase_col!r}")
        phrase_list = phrases[phrase_col].astype(str).tolist()
    else:
        phrase_list = [str(p) for p in phrases]
    units = example_phrases_for_soft_topics(
        phrase_list, R, n_top=max(n_examples, 1), n_sample=0, seed=seed
    )
    dirty_set = set(int(d) for d in (dirty or ()))
    proposed_set = set(int(d) for d in (proposed or ()))
    label_list = list(labels) if labels is not None else None
    parent_map: dict[int, str] = {}
    if isinstance(parent_labels, dict):
        parent_map = {int(k): str(v) for k, v in parent_labels.items() if v}
    elif parent_labels is not None:
        for j, pl in enumerate(parent_labels):
            if pl is not None and str(pl) != "":
                parent_map[j] = str(pl)
    rows = []
    for u in units:
        c = int(u["cluster"])
        examples = u.get("examples") or []
        name = None
        if label_list is not None and c < len(label_list):
            name = label_list[c]
        is_dirty = c in dirty_set
        if name is None or name == "":
            name = "unnamed / stale" if is_dirty else f"topic {c}"
        rows.append(
            {
                "topic": c,
                "label": name,
                "parent_label": parent_map.get(c, ""),
                "proposed": c in proposed_set,
                "dirty": is_dirty,
                "n_examples": len(examples),
                "examples": "; ".join(str(e) for e in examples[:n_examples]),
                "mass": float(R[:, c].sum()),
                "n_map": int((np.argmax(R, axis=1) == c).sum()),
                "key": u.get("key", ""),
            }
        )
    return pd.DataFrame(rows)


def subject_grain_diagnostics(fit: dict[str, Any]) -> dict[str, Any]:
    """Machine-screen flags (collapse / tiny mass) — not a grain selector."""
    diag = topic_fit_diagnostics(fit)
    R = np.asarray(fit["responsibilities"], dtype=float)
    map_sizes = np.bincount(
        responsibilities_to_labels(R), minlength=int(fit.get("k", R.shape[1]))
    )
    tiny = [int(j) for j, n in enumerate(map_sizes) if 0 < n < 3]
    empty = [int(j) for j, n in enumerate(map_sizes) if n == 0]
    return {
        **diag,
        "tiny_topics": tiny,
        "empty_topics": empty,
    }


def _logsumexp(a: np.ndarray, axis: int | None = None) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    m = np.max(a, axis=axis, keepdims=True)
    m_safe = np.where(np.isfinite(m), m, 0.0)
    s = np.exp(a - m_safe).sum(axis=axis, keepdims=True)
    out = np.log(np.clip(s, 1e-300, None)) + m_safe
    if axis is not None:
        out = np.squeeze(out, axis=axis)
    return out


def parent_split_kl(
    X: np.ndarray,
    parent_mass: np.ndarray,
    parent_component_fit: dict[str, Any],
    child_component_fits: Sequence[dict[str, Any]],
    child_pi: np.ndarray,
    sigma2: float,
) -> float:
    """KL̂(parent ‖ child-mix) under the parent soft mass.

    For each point ``n``, compare the parent PPCA density to the local
    child mixture ``Σ_j π_j p_j``, then take the parent-mass expectation:

    ``Σ_n m_n [log p_parent(x_n) − log p_mix(x_n)] / Σ_n m_n``.

    Dendrogram edge lengths use ``abs`` of this value so a better-fitting
    split still yields a positive branch length.
    """
    X = np.asarray(X, dtype=float)
    m = np.asarray(parent_mass, dtype=float).ravel()
    if X.ndim != 2 or m.shape[0] != X.shape[0]:
        raise ValueError("X and parent_mass length mismatch")
    if parent_component_fit is None or not child_component_fits:
        return 0.0
    wsum = float(m.sum())
    if wsum <= 0.0 or not np.isfinite(wsum):
        return 0.0
    s2 = float(sigma2)
    log_p = log_likelihood_ppca(X, parent_component_fit, s2)
    log_c = np.column_stack(
        [log_likelihood_ppca(X, cf, s2) for cf in child_component_fits]
    )
    pi = np.asarray(child_pi, dtype=float).ravel()
    if pi.shape[0] != log_c.shape[1]:
        pi = np.full(log_c.shape[1], 1.0 / log_c.shape[1])
    log_pi = np.log(np.clip(pi, 1e-300, None))
    log_mix = _logsumexp(log_c + log_pi[None, :], axis=1)
    kl_n = np.asarray(log_p, float) - np.asarray(log_mix, float)
    kl_n = np.where(np.isfinite(kl_n), kl_n, 0.0)
    return float((m * kl_n).sum() / wsum)


def dendrogram_new(k: int, *, labels: dict[int, str] | None = None) -> dict[str, Any]:
    """Fresh split-only dendrogram: one leaf per current topic at height 0."""
    k = int(k)
    labels = labels or {}
    nodes: dict[int, dict[str, Any]] = {}
    leaf_of_topic: dict[int, int] = {}
    for j in range(k):
        nodes[j] = {
            "kind": "leaf",
            "topic_id": j,
            "label": str(labels.get(j, f"topic {j}")),
            "children": None,
            "height": 0.0,
            "kl": None,
            "parent": None,
        }
        leaf_of_topic[j] = j
    return {
        "active": True,
        "abandoned_reason": None,
        "nodes": nodes,
        "leaf_of_topic": leaf_of_topic,
        "next_id": k,
        "roots": list(range(k)),
    }


def dendrogram_abandon(
    tree: dict[str, Any] | None,
    *,
    reason: str = "merge",
) -> dict[str, Any]:
    """Clear hierarchy after a merge (divisive tree no longer valid)."""
    return {
        "active": False,
        "abandoned_reason": str(reason),
        "nodes": {},
        "leaf_of_topic": {},
        "next_id": 0,
        "roots": [],
    }


def dendrogram_record_split(
    tree: dict[str, Any],
    *,
    parent_topic: int,
    child_topics: Sequence[int],
    kl: float,
    labels: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Replace the parent leaf with an internal node; children become leaves.

    ``child_topics`` must already be mass-ordered (largest first). Topic ids
    elsewhere are remapped as in :func:`propose_split` (ids ``> parent`` shift
    by ``len(children) - 1``).
    """
    if not tree or not tree.get("active", False):
        return tree
    tree = deepcopy(tree)
    labels = labels or {}
    parent_topic = int(parent_topic)
    children = [int(c) for c in child_topics]
    n_ch = len(children)
    if n_ch < 2:
        raise ValueError("dendrogram split needs at least two children")
    leaf_map: dict[int, int] = {
        int(t): int(nid) for t, nid in tree["leaf_of_topic"].items()
    }
    if parent_topic not in leaf_map:
        return tree
    parent_nid = leaf_map.pop(parent_topic)
    # Remap surviving leaves for index shift after inserting children at parent
    shifted: dict[int, int] = {}
    for tid, nid in leaf_map.items():
        if tid < parent_topic:
            shifted[tid] = nid
        elif tid > parent_topic:
            shifted[tid + n_ch - 1] = nid
            tree["nodes"][nid]["topic_id"] = tid + n_ch - 1
    leaf_map = shifted

    length = abs(float(kl))
    if not np.isfinite(length):
        length = 0.0
    parent_node = tree["nodes"][parent_nid]
    # Leaves stay at y=0; this split sits at |KL| above the children.
    split_h = length
    child_nids: list[int] = []
    for c in children:
        nid = int(tree["next_id"])
        tree["next_id"] = nid + 1
        tree["nodes"][nid] = {
            "kind": "leaf",
            "topic_id": c,
            "label": str(labels.get(c, f"topic {c}")),
            "children": None,
            "height": 0.0,
            "kl": None,
            "parent": parent_nid,
        }
        leaf_map[c] = nid
        child_nids.append(nid)
    tree["nodes"][parent_nid] = {
        "kind": "split",
        "topic_id": None,
        "label": str(parent_node.get("label") or f"topic {parent_topic}"),
        "children": child_nids,
        "height": split_h,
        "kl": length,
        "parent": parent_node.get("parent"),
    }
    # Roots: remove parent leaf if it was a root; keep parent as root if it was
    roots = [int(r) for r in tree.get("roots") or []]
    if parent_nid not in roots:
        # parent was under another split — roots unchanged
        pass
    tree["leaf_of_topic"] = leaf_map
    tree["roots"] = roots if roots else [parent_nid]
    # Refresh leaf labels
    for tid, nid in leaf_map.items():
        if labels and tid in labels:
            tree["nodes"][nid]["label"] = str(labels[tid])
    return tree


def dendrogram_sync_labels(
    tree: dict[str, Any],
    labels: dict[int, str],
) -> dict[str, Any]:
    """Update leaf display names from the live catalogue labels."""
    if not tree or not tree.get("active"):
        return tree
    tree = deepcopy(tree)
    for tid, nid in tree.get("leaf_of_topic", {}).items():
        nid = int(nid)
        if nid in tree["nodes"] and int(tid) in labels:
            tree["nodes"][nid]["label"] = str(labels[int(tid)])
    return tree
