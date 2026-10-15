"""Document-level weighting, bootstrap intervals, and agreement helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd


def doc_profile(
    df: pd.DataFrame,
    col: str,
    values: list,
    *,
    doc_col: str = "doc_id",
) -> pd.DataFrame:
    """Per document, the share of its points in each value of ``col`` (rows: documents)."""
    ct = pd.crosstab(df[doc_col], df[col]).reindex(columns=values, fill_value=0)
    return ct.div(ct.sum(axis=1), axis=0)


def group_compare(
    df: pd.DataFrame,
    group_col: str,
    col: str,
    values: list | None,
    rng: np.random.Generator,
    *,
    doc_col: str = "doc_id",
    reps: int = 2000,
    min_gap: float = 3.0,
    groups: list | None = None,
) -> pd.DataFrame:
    """Document-weighted share of each value in each group, with 95% cluster-bootstrap intervals.

    When exactly two groups are present, also reports group2-minus-group1 difference columns.
    """
    values = values or sorted(df[col].dropna().unique())
    groups = groups or sorted(df[group_col].dropna().unique())
    if len(groups) < 1:
        return pd.DataFrame()
    P = {g: doc_profile(df[df[group_col] == g], col, values, doc_col=doc_col) for g in groups}
    if any(len(p) == 0 for p in P.values()):
        return pd.DataFrame()
    B = {}
    for g, p in P.items():
        a = p.values
        idx = rng.integers(0, len(a), size=(reps, len(a)))
        B[g] = a[idx].mean(1) * 100
    out = pd.DataFrame({col: values})
    for g in groups:
        safe = str(g)
        out[f"{safe}_pct"] = (P[g].mean() * 100).values
        out[f"{safe}_lo"] = np.percentile(B[g], 2.5, 0)
        out[f"{safe}_hi"] = np.percentile(B[g], 97.5, 0)
        out[f"docs_{safe}"] = len(P[g])
    if len(groups) == 2:
        g0, g1 = groups
        d = B[g1] - B[g0]
        out["difference"] = out[f"{g1}_pct"] - out[f"{g0}_pct"]
        out["diff_lo"] = np.percentile(d, 2.5, 0)
        out["diff_hi"] = np.percentile(d, 97.5, 0)
        out["clear"] = ((out.diff_lo > 0) | (out.diff_hi < 0)) & (out.difference.abs() >= min_gap)
    return out.round(1)


def doc_binary_presence(
    df: pd.DataFrame,
    cluster_col: str,
    period_col: str,
    *,
    doc_col: str = "doc_id",
) -> pd.DataFrame:
    """Fraction of documents per period that raise each cluster (document-level binary weighting)."""
    docs = df[[doc_col, period_col, cluster_col]].drop_duplicates()
    n_docs = df.groupby(period_col)[doc_col].nunique()
    counts = docs.groupby([period_col, cluster_col])[doc_col].nunique().unstack(fill_value=0)
    shares = counts.div(n_docs, axis=0)
    return shares


def cluster_boot_share(flag, cluster, rng: np.random.Generator, reps: int = 1000):
    """Point-level share (%) with a 95% interval, resampling documents."""
    d = pd.DataFrame({"y": np.asarray(flag, float), "k": np.asarray(cluster)})
    g = d.groupby("k").y.agg(["sum", "size"])
    s, n = g["sum"].to_numpy(), g["size"].to_numpy()
    idx = rng.integers(0, len(s), size=(reps, len(s)))
    b = 100 * s[idx].sum(1) / np.maximum(n[idx].sum(1), 1)
    return 100 * s.sum() / n.sum(), np.percentile(b, 2.5), np.percentile(b, 97.5), s, n


def jsd(p, q) -> float:
    """Jensen–Shannon divergence (base 2, 0–1) between two distributions."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(a, b):
        return np.sum(
            np.where(a > 0, a * np.log2(np.where(a > 0, a, 1) / np.where(b > 0, b, 1)), 0)
        )

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


def kappa(a, b) -> float:
    a, b = list(a), list(b)
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return float("nan") if pe == 1 else round((po - pe) / (1 - pe), 2)


def rank_agreement(main: pd.Series, other: pd.Series, min_gap: float = 3.0):
    """Rank correlation of two sets of differences, and % same direction where |main| >= min_gap."""
    j = pd.concat([main.rename("main"), other.rename("other")], axis=1).dropna()
    if len(j) < 3:
        return np.nan, np.nan, len(j)
    rho = np.corrcoef(j.main.rank(), j.other.rank())[0, 1]
    big = j[j.main.abs() >= min_gap]
    same = (np.sign(big.main) == np.sign(big.other)).mean() if len(big) else np.nan
    return round(rho, 2), (round(100 * same, 0) if same == same else np.nan), len(j)
