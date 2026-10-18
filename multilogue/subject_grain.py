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
    max_iter: int = 30,
) -> dict[str, Any]:
    """CIP-0017-style σ² pick without destroying interactive soft assignments.

    For each grid value, run full-mixture EM from the *current* ``R``, then
    choose the softest non-collapsing floor (largest σ² among viable fits).
    """
    X = np.asarray(X, float)
    R0 = np.asarray(R, float)
    if R0.ndim != 2 or R0.shape[0] != X.shape[0]:
        raise ValueError("R must be (n, k) aligned with X")
    k = int(R0.shape[1])
    grid_vals = list(grid) if grid is not None else list(DEFAULT_TOPIC_SIGMA2_GRID)
    min_map = 1 if k == 1 else max(2, int(np.ceil(0.5 * k)))
    curve: list[dict[str, Any]] = []
    fits: dict[float, dict[str, Any]] = {}
    for s2 in sorted(float(s) for s in grid_vals):
        fit = _fit_from_responsibilities(
            X, R0.copy(), s2, seed=seed, max_iter=max_iter
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
        best = max(viable, key=lambda d: float(d["sigma2"]))
        selection = "softest_noncollapse_held_R"
    else:
        best = max(
            curve,
            key=lambda d: (int(d["n_map"]), -float(d["max_mean_cos"])),
        )
        selection = "fallback_least_collapsed_held_R"
    s2_star = float(best["sigma2"])
    out = fits[s2_star]
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
    child_ids = list(range(i, i + n_children))
    history_entry = {
        "action": "split",
        "topic": i,
        "children": child_ids,
        "n_children": n_children,
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
