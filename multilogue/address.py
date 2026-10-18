"""Address-stage helpers: question-facing curation and soft re-compare.

Access loads units; Assess characterises them without the research question.
Address applies analysis choices — including researcher cluster/lens edits —
and recomputes soft / document-distance contrasts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .soft import compute_mixture_weights, soft_mapping_from_hard
from .weight import group_compare, soft_group_compare

# German municipal cycling: parking / locking vocabulary in cluster 0 noise.
DEFAULT_PARKING_PATTERN = r"park|stell|abstell|anschlie[sß]"


def centroids_from_labels(
    E: np.ndarray,
    labels: np.ndarray,
    k: int | None = None,
) -> np.ndarray:
    """Mean unit-norm centroids for cluster ids ``0..k-1`` (empty → ones)."""
    labels = np.asarray(labels, dtype=int)
    if k is None:
        k = int(labels.max()) + 1 if len(labels) else 0
    cents = []
    for c in range(k):
        m = labels == c
        if m.any():
            v = E[m].mean(0)
        else:
            v = np.ones(E.shape[1], dtype=float)
        cents.append(v)
    C = np.vstack(cents)
    return C / np.linalg.norm(C, axis=1, keepdims=True)


def lens_map_from_phrases(phrases: pd.DataFrame) -> dict[int, str]:
    """Hard lens of each present cluster id (first row wins)."""
    out: dict[int, str] = {}
    for c, g in phrases.groupby("cluster"):
        out[int(c)] = str(g["lens"].iloc[0])
    return out


def edited_lens_yaml(lens_of: dict[int, str], *, header: str = "") -> str:
    """YAML body mapping lens name → cluster id list (researcher-edit format)."""
    by: dict[str, list[int]] = {}
    for c, L in sorted(lens_of.items()):
        by.setdefault(str(L), []).append(int(c))
    lines = [header] if header else []
    if not lines or not lines[0].startswith("#"):
        lines = ["# Researcher-edited lens mapping"] + ([header] if header else [])
    for L, cs in sorted(by.items()):
        lines.append(f"{json.dumps(L)}: {sorted(cs)}")
    return "\n".join(lines) + "\n"


def move_phrases_by_keyword(
    phrases: pd.DataFrame,
    *,
    from_cluster: int,
    to_cluster: int,
    pattern: str = DEFAULT_PARKING_PATTERN,
    phrase_col: str = "phrase",
    to_label: str | None = None,
    to_lens: str | None = None,
) -> tuple[pd.DataFrame, int]:
    """Reassign keyword-matching phrases from one cluster to another."""
    ph = phrases.copy()
    rx = re.compile(pattern, re.I)
    move = (ph["cluster"] == from_cluster) & ph[phrase_col].astype(str).str.contains(
        rx, na=False
    )
    n = int(move.sum())
    if n:
        ph.loc[move, "cluster"] = to_cluster
        if to_label is not None:
            ph.loc[move, "cluster_label"] = to_label
        if to_lens is not None:
            ph.loc[move, "lens"] = to_lens
    return ph, n


def _nearest_cluster(
    E: np.ndarray,
    labels: np.ndarray,
    src: int,
    candidates: Sequence[int],
) -> int:
    C = {
        c: E[labels == c].mean(0)
        for c in candidates
        if (labels == c).any()
    }
    if not C:
        raise ValueError("no candidate clusters to merge into")
    v = E[labels == src].mean(0)
    vn = v / (np.linalg.norm(v) + 1e-9)

    def dist(c: int) -> float:
        u = C[c]
        return float(1.0 - np.dot(vn, u / (np.linalg.norm(u) + 1e-9)))

    return min(C, key=dist)


def merge_cluster_into(
    phrases: pd.DataFrame,
    E: np.ndarray,
    src: int,
    dst: int,
) -> pd.DataFrame:
    """Move all phrases in ``src`` into ``dst``, inheriting dst label/lens."""
    ph = phrases.copy()
    labels = ph["cluster"].to_numpy()
    if not (labels == src).any():
        return ph
    dst_lens = str(ph.loc[ph["cluster"] == dst, "lens"].iloc[0])
    dst_label = str(ph.loc[ph["cluster"] == dst, "cluster_label"].iloc[0])
    ph.loc[ph["cluster"] == src, "cluster"] = dst
    ph.loc[ph["cluster"] == dst, "lens"] = dst_lens
    ph.loc[ph["cluster"] == dst, "cluster_label"] = dst_label
    return ph


def free_cluster_slot(
    phrases: pd.DataFrame,
    E: np.ndarray,
    *,
    protect: int,
) -> tuple[pd.DataFrame, int, int]:
    """Free a cluster id by merging a singleton (else smallest) into its neighbour.

    Returns ``(phrases, freed_id, merge_target)``. ``protect`` is never merged away
    (typically the oversized bag we are about to split).
    """
    ph = phrases.copy()
    sizes = ph.groupby("cluster").size()
    singleton = [int(c) for c, n in sizes.items() if n == 1 and int(c) != protect]
    if singleton:
        src = singleton[0]
    else:
        candidates = [int(c) for c in sizes.index if int(c) != protect]
        if not candidates:
            raise ValueError("no cluster available to free")
        src = int(sizes.loc[candidates].idxmin())
    others = [int(c) for c in sizes.index if int(c) not in (src, protect)]
    labels = ph["cluster"].to_numpy()
    dst = _nearest_cluster(E, labels, src, others)
    ph = merge_cluster_into(ph, E, src, dst)
    return ph, src, dst


def bisect_cluster(
    phrases: pd.DataFrame,
    E: np.ndarray,
    cluster_id: int,
    free_id: int,
    *,
    majority_label: str,
    minority_label: str,
    lens: str,
    seed: int = 0,
    min_size: int = 8,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Secondary 2-means on one cluster; majority stays, minority → ``free_id``."""
    ph = phrases.copy()
    mask = ph["cluster"].to_numpy() == cluster_id
    info: dict[str, Any] = {"split": False, "cluster": cluster_id, "free_id": free_id}
    if int(mask.sum()) < min_size:
        info["reason"] = f"size {int(mask.sum())} < min_size {min_size}"
        return ph, info
    km = KMeans(n_clusters=2, random_state=seed, n_init=10).fit(E[mask])
    maj = int(np.bincount(km.labels_).argmax())
    new = np.where(km.labels_ == maj, cluster_id, free_id)
    idx = np.flatnonzero(mask)
    ph.loc[ph.index[idx], "cluster"] = new
    ph.loc[ph["cluster"] == cluster_id, "cluster_label"] = majority_label
    ph.loc[ph["cluster"] == free_id, "cluster_label"] = minority_label
    ph.loc[ph["cluster"] == cluster_id, "lens"] = lens
    ph.loc[ph["cluster"] == free_id, "lens"] = lens
    info.update(
        {
            "split": True,
            "n_majority": int((new == cluster_id).sum()),
            "n_minority": int((new == free_id).sum()),
        }
    )
    return ph, info


def tighten_cimt_parking_path(
    phrases: pd.DataFrame,
    E: np.ndarray,
    *,
    parking_from: int = 0,
    parking_to: int = 6,
    parking_pattern: str = DEFAULT_PARKING_PATTERN,
    parking_label: str = "Fahrradstellplätze verbessern",
    parking_lens: str = "Parken und Abstellen",
    path_lens: str = "Radwege und Führung",
    path_majority_label: str = "Radweg-Konflikte und Belag",
    path_minority_label: str = "Routenführung und Umleitung",
    seed: int = 0,
) -> dict[str, Any]:
    """CIMT formats tightening: parking keyword merge + split oversized path bag.

    Returns phrases plus a notes dict (moves, merges, split). Does not call an LLM.
    """
    notes: dict[str, Any] = {}
    ph, n_move = move_phrases_by_keyword(
        phrases,
        from_cluster=parking_from,
        to_cluster=parking_to,
        pattern=parking_pattern,
        to_label=parking_label,
        to_lens=parking_lens,
    )
    notes["parking_moved"] = n_move

    sizes = ph.groupby("cluster").size()
    big = int(sizes.idxmax())
    ph, freed, merged_into = free_cluster_slot(ph, E, protect=big)
    notes["freed"] = freed
    notes["merged_into"] = merged_into
    notes["split_source"] = big

    ph, split_info = bisect_cluster(
        ph,
        E,
        big,
        freed,
        majority_label=path_majority_label,
        minority_label=path_minority_label,
        lens=path_lens,
        seed=seed,
    )
    notes["split"] = split_info

    if (ph["cluster"] == parking_from).any():
        ph.loc[ph["cluster"] == parking_from, "lens"] = path_lens
    if (ph["cluster"] == parking_to).any():
        ph.loc[ph["cluster"] == parking_to, "lens"] = parking_lens

    return {
        "phrases": ph,
        "notes": notes,
        "lens_of": lens_map_from_phrases(ph),
    }


def recompute_format_contrasts(
    phrases: pd.DataFrame,
    E: np.ndarray,
    *,
    sigma2: float,
    group_col: str = "format",
    groups: Sequence[str] = ("dialogue", "survey"),
    reps: int = 400,
    seed: int = 0,
    min_phrases: int = 3,
    n_perm: int = 399,
    include_distance: bool = True,
) -> dict[str, Any]:
    """Hard lens compare, soft mixture weights/compare, optional document EMD."""
    from . import distance as dd

    rng = np.random.default_rng(seed)
    lens_of = lens_map_from_phrases(phrases)
    k = int(phrases["cluster"].max()) + 1
    cents = centroids_from_labels(E, phrases["cluster"].to_numpy(), k)
    hard = group_compare(
        phrases, group_col, "lens", None, rng, reps=reps, groups=list(groups)
    )
    soft_map = soft_mapping_from_hard(lens_of)
    W, lens_names = compute_mixture_weights(cents, soft_map, float(sigma2))
    soft = soft_group_compare(
        phrases, W, lens_names, group_col, rng, groups=list(groups), reps=reps
    )
    out: dict[str, Any] = {
        "lens_of": lens_of,
        "centroids": cents,
        "hard_compare": hard,
        "soft_compare": soft,
        "W": W,
        "lens_names": lens_names,
        "sigma2": float(sigma2),
    }
    if include_distance:
        doc_group = (
            phrases.groupby("doc_id")[group_col]
            .agg(lambda s: s.mode().iloc[0])
            .to_dict()
        )
        out["distance"] = dd.run_document_distance_analysis(
            phrases,
            cents,
            doc_group,
            min_phrases=min_phrases,
            n_perm=n_perm,
            seed=seed + 1,
        )
    return out


def write_curated_tables(
    out_dir: str | Path,
    phrases: pd.DataFrame,
    contrasts: dict[str, Any],
    *,
    yaml_header: str = "# Researcher-edited lens mapping after curation",
) -> Path:
    """Write curated phrases, compares, mixture weights, and edited lens YAML."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    phrases.to_csv(out / "phrases_clustered.csv", index=False)
    contrasts["hard_compare"].to_csv(
        out / "group_compare_format_lenses.csv", index=False
    )
    contrasts["soft_compare"].to_csv(
        out / "soft_group_compare_format.csv", index=False
    )
    pd.DataFrame(contrasts["W"], columns=contrasts["lens_names"]).to_csv(
        out / "lens_mixture_weights.csv", index_label="cluster"
    )
    (out / "edited_lenses.yaml").write_text(
        edited_lens_yaml(contrasts["lens_of"], header=yaml_header),
        encoding="utf-8",
    )
    return out
