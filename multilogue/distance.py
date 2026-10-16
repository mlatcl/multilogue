"""Document-level distance analysis (EMD + MDS + PERMANOVA / PERMDISP).

Tests whether documents from different groups differ in *what they raise*
(cluster shares), without using LLM framing lenses or soft mixture weights.

Requires the optional ``pot`` extra::

    pip install 'multilogue[distance]'
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _require_ot():
    try:
        import ot
    except ImportError as exc:
        raise ImportError(
            "POT is required: pip install pot (or pip install 'multilogue[distance]')"
        ) from exc
    return ot


def document_cluster_distributions(
    phrases_df: pd.DataFrame,
    n_clusters: int,
    doc_col: str = "doc_id",
    cluster_col: str = "cluster",
    min_phrases: int = 50,
) -> Tuple[np.ndarray, List[str], pd.Series]:
    """Share of each document's phrases falling in each cluster.

    Documents with fewer than *min_phrases* phrases are dropped.
    """
    counts = (
        phrases_df.groupby([doc_col, cluster_col])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=range(n_clusters), fill_value=0)
    )
    totals = counts.sum(axis=1)
    counts = counts[totals >= min_phrases]
    totals = totals[totals >= min_phrases]
    P = counts.to_numpy(dtype=float) / totals.to_numpy(dtype=float)[:, None]
    return P, counts.index.tolist(), totals


def cosine_ground_cost(centroids: np.ndarray) -> np.ndarray:
    """Cosine distance between cluster centroids (K × K, zero diagonal)."""
    C = np.asarray(centroids, dtype=float)
    C = C / np.linalg.norm(C, axis=1, keepdims=True)
    M = 1.0 - C @ C.T
    np.fill_diagonal(M, 0.0)
    return np.clip(M, 0.0, None)


def emd_distance_matrix(P: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Pairwise Earth Mover's Distance between the rows of *P* under cost *M*."""
    ot = _require_ot()
    M = np.ascontiguousarray(M, dtype=np.float64)
    n = P.shape[0]
    D = np.zeros((n, n))
    for i in range(n):
        a = np.ascontiguousarray(P[i], dtype=np.float64)
        for j in range(i + 1, n):
            b = np.ascontiguousarray(P[j], dtype=np.float64)
            D[i, j] = D[j, i] = ot.emd2(a, b, M)
    return D


def classical_mds(D: np.ndarray, n_components: int = 2) -> Dict[str, object]:
    """Classical (Torgerson) MDS / principal coordinates analysis."""
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, V = np.linalg.eigh(B)
    order = np.argsort(w)[::-1]
    w, V = w[order], V[:, order]
    pos = w > 1e-12
    pos_sum = w[pos].sum()
    full = V[:, pos] * np.sqrt(w[pos])
    return {
        "coords": full[:, :n_components],
        "eigenvalues": w,
        "explained": w[:n_components] / pos_sum,
        "negative_ratio": float(-w[w < -1e-12].sum() / pos_sum),
        "full_coords": full,
    }


def _pseudo_f(D2: np.ndarray, groups: np.ndarray) -> Tuple[float, float]:
    n = len(groups)
    labels = np.unique(groups)
    a = len(labels)
    iu = np.triu_indices(n, 1)
    ss_total = D2[iu].sum() / n
    ss_within = 0.0
    for g in labels:
        idx = np.where(groups == g)[0]
        if len(idx) > 1:
            sub = D2[np.ix_(idx, idx)]
            ss_within += sub[np.triu_indices(len(idx), 1)].sum() / len(idx)
    ss_between = ss_total - ss_within
    f = (ss_between / (a - 1)) / (ss_within / (n - a))
    return f, ss_between / ss_total


def permanova(
    D: np.ndarray, groups: Sequence, n_perm: int = 9999, seed: int = 42
) -> Dict[str, float]:
    """One-way PERMANOVA on distance matrix *D*."""
    groups = np.asarray(groups)
    D2 = np.asarray(D) ** 2
    f_obs, r2 = _pseudo_f(D2, groups)
    rng = np.random.default_rng(seed)
    exceed = sum(
        _pseudo_f(D2, rng.permutation(groups))[0] >= f_obs for _ in range(n_perm)
    )
    return {
        "pseudo_F": f_obs,
        "R2": r2,
        "p_value": (1 + exceed) / (1 + n_perm),
        "n_docs": len(groups),
        "n_groups": len(np.unique(groups)),
    }


def permdisp(
    D: np.ndarray, groups: Sequence, n_perm: int = 9999, seed: int = 42
) -> Dict[str, object]:
    """Test whether groups differ in multivariate dispersion."""
    groups = np.asarray(groups)
    X = classical_mds(np.asarray(D))["full_coords"]
    labels = np.unique(groups)
    z = np.zeros(len(groups))
    for g in labels:
        idx = groups == g
        z[idx] = np.linalg.norm(X[idx] - X[idx].mean(axis=0), axis=1)

    def _anova_f(values, grp):
        grand = values.mean()
        ssb = sum(
            (grp == g).sum() * (values[grp == g].mean() - grand) ** 2 for g in labels
        )
        ssw = sum(
            ((values[grp == g] - values[grp == g].mean()) ** 2).sum() for g in labels
        )
        return (ssb / (len(labels) - 1)) / (ssw / (len(values) - len(labels)))

    f_obs = _anova_f(z, groups)
    rng = np.random.default_rng(seed)
    exceed = sum(
        _anova_f(z, rng.permutation(groups)) >= f_obs for _ in range(n_perm)
    )
    return {
        "F": f_obs,
        "p_value": (1 + exceed) / (1 + n_perm),
        "mean_distance_to_centroid": {
            g: float(z[groups == g].mean()) for g in labels
        },
    }


def pairwise_permanova(
    D: np.ndarray, groups: Sequence, n_perm: int = 9999, seed: int = 42
) -> pd.DataFrame:
    """PERMANOVA and PERMDISP for every pair of groups."""
    groups = np.asarray(groups)
    labels = list(np.unique(groups))
    pairs = list(combinations(labels, 2))
    rows = []
    for g1, g2 in pairs:
        mask = np.isin(groups, [g1, g2])
        Dm, gm = D[np.ix_(mask, mask)], groups[mask]
        res = permanova(Dm, gm, n_perm, seed)
        disp = permdisp(Dm, gm, n_perm, seed)
        spread = disp["mean_distance_to_centroid"]
        rows.append(
            {
                "comparison": f"{g1} vs {g2}",
                **res,
                "dispersion_F": disp["F"],
                "dispersion_p": disp["p_value"],
                "spread_first": spread[g1],
                "spread_second": spread[g2],
            }
        )
    out = pd.DataFrame(rows)
    out["p_bonferroni"] = np.minimum(1.0, out["p_value"] * len(pairs))
    out["dispersion_p_bonferroni"] = np.minimum(
        1.0, out["dispersion_p"] * len(pairs)
    )
    return out


def axis_correlates(
    coords: np.ndarray,
    P: np.ndarray,
    cluster_names: Dict[int, str],
    top: int = 5,
) -> pd.DataFrame:
    """Clusters whose document shares correlate most with each MDS axis."""
    rows = []
    for a in range(coords.shape[1]):
        r = np.array(
            [
                np.corrcoef(coords[:, a], P[:, k])[0, 1]
                if P[:, k].std() > 0
                else 0.0
                for k in range(P.shape[1])
            ]
        )
        order = np.argsort(r)
        for end, idxs in [("negative", order[:top]), ("positive", order[::-1][:top])]:
            for k in idxs:
                rows.append(
                    {
                        "axis": a + 1,
                        "end": end,
                        "cluster_id": int(k),
                        "label": cluster_names.get(int(k), f"Cluster {k}"),
                        "r": float(r[k]),
                    }
                )
    return pd.DataFrame(rows)


def run_document_distance_analysis(
    phrases_df: pd.DataFrame,
    centroids: np.ndarray,
    doc_group: Dict[str, str],
    cluster_names: Optional[Dict[int, str]] = None,
    min_phrases: int = 50,
    n_perm: int = 9999,
    seed: int = 42,
    doc_col: str = "doc_id",
    cluster_col: str = "cluster",
) -> Dict[str, object]:
    """Full EMD → MDS → PERMANOVA/PERMDISP pipeline."""
    K = centroids.shape[0]
    P, docs, n_phr = document_cluster_distributions(
        phrases_df,
        K,
        doc_col=doc_col,
        cluster_col=cluster_col,
        min_phrases=min_phrases,
    )
    groups = np.array([doc_group[d] for d in docs])
    M = cosine_ground_cost(centroids)
    D = emd_distance_matrix(P, M)
    mds = classical_mds(D, 2)
    dropped = sorted(set(phrases_df[doc_col]) - set(docs))
    return {
        "docs": docs,
        "groups": groups,
        "n_phrases": n_phr.to_numpy(),
        "P": P,
        "D": D,
        "mds": mds,
        "dropped_docs": dropped,
        "permanova": permanova(D, groups, n_perm, seed),
        "pairwise": pairwise_permanova(D, groups, n_perm, seed),
        "permdisp": permdisp(D, groups, n_perm, seed),
        "axes": axis_correlates(mds["coords"], P, cluster_names or {}),
    }
