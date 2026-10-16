"""Question-agnostic diagnostic plots for pedagogical notebooks.

Requires matplotlib (``pip install multilogue[report]`` or ``[dev]``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
PALETTE = ["#2a78d6", "#eb6834", "#3d9b8f", "#8b5cf6", "#c45c26", "#5a6a7a"]


def _plt():
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "matplotlib is required for multilogue.viz; install multilogue[report]."
        ) from e
    return plt


def tidy(ax) -> None:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.set_axisbelow(True)


def save(fig, path: str | Path | None = None, *, show: bool = True):
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=160, bbox_inches="tight")
    if show:
        _plt().show()
    else:
        _plt().close(fig)
    return path


def unit_size_hist(
    sizes: pd.DataFrame,
    *,
    group_col: str | None = None,
    units: Sequence[dict] | None = None,
    path: str | Path | None = None,
    show: bool = True,
):
    """Histogram of unit word counts, optionally faceted by a unit metadata group."""
    plt = _plt()
    df = sizes.copy()
    if group_col and units is not None and group_col not in df.columns:
        gmap = {u["unit_id"]: u.get(group_col) for u in units}
        df[group_col] = df["unit_id"].map(gmap)
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    if group_col and group_col in df.columns:
        for i, (g, sub) in enumerate(df.groupby(group_col)):
            ax.hist(
                sub["n_words"],
                bins=20,
                alpha=0.55,
                label=str(g),
                color=PALETTE[i % len(PALETTE)],
            )
        ax.legend(frameon=False, fontsize=9)
    else:
        ax.hist(df["n_words"], bins=20, color=PALETTE[0], alpha=0.85)
    ax.set_xlabel("Words per unit")
    ax.set_ylabel("Count")
    ax.set_title("Unit sizes (Assess)", loc="left", color=INK, fontsize=11)
    ax.axvline(4, color=MUTED, ls="--", lw=1, label="min_words=4")
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)


def docs_per_group_bars(
    docs: pd.DataFrame,
    *,
    path: str | Path | None = None,
    show: bool = True,
):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ax.barh(docs["group"].astype(str), docs["n_docs"], color=PALETTE[0])
    ax.invert_yaxis()
    ax.set_xlabel("Documents")
    ax.set_title("Documents per group (Assess)", loc="left", color=INK, fontsize=11)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)


def yield_bars(
    yield_df: pd.DataFrame,
    *,
    path: str | Path | None = None,
    show: bool = True,
):
    """Bars of phrases kept and % units returning none, by group × kind."""
    plt = _plt()
    df = yield_df.copy()
    if "group" in df.columns and "kind" in df.columns:
        labels = df["group"].astype(str) + " / " + df["kind"].astype(str)
    else:
        labels = df.index.astype(str)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 0.42 * len(df) + 1.8))
    y = np.arange(len(df))
    kept = df["kept"].to_numpy(float) if "kept" in df.columns else df.select_dtypes("number").iloc[:, 0]
    axes[0].barh(y, kept, color=PALETTE[0])
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(list(labels))
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Phrases kept")
    axes[0].set_title("Yield: kept phrases", loc="left", color=INK, fontsize=11)
    tidy(axes[0])
    if "pct_units_none" in df.columns:
        axes[1].barh(y, df["pct_units_none"], color=PALETTE[1])
        axes[1].set_xlabel("% units with none")
    else:
        axes[1].axis("off")
    axes[1].set_yticks([])
    axes[1].set_title("Empty replies", loc="left", color=INK, fontsize=11)
    tidy(axes[1])
    fig.tight_layout()
    return save(fig, path, show=show)


def cluster_size_bars(
    phrases: pd.DataFrame,
    *,
    cluster_col: str = "cluster",
    path: str | Path | None = None,
    show: bool = True,
):
    plt = _plt()
    counts = phrases[cluster_col].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.bar(counts.index.astype(str), counts.values, color=PALETTE[2])
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Phrases")
    ax.set_title("Cluster sizes", loc="left", color=INK, fontsize=11)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)


def embedding_scatter(
    embeddings: np.ndarray,
    labels: Sequence,
    *,
    title: str = "Embedding space (first two PCA axes)",
    path: str | Path | None = None,
    show: bool = True,
):
    """2D PCA projection of phrase embeddings coloured by cluster or lens.

    Classical PCA here is a viewing algorithm (directions of high variance), not
    a probabilistic PCA generative model. Soft PPCA memberships and σ² sweeps
    live in :mod:`multilogue.soft`; this plot only makes the local clustering
    assumption inspectable.
    """
    plt = _plt()
    from sklearn.decomposition import PCA

    X = np.asarray(embeddings, float)
    if X.ndim != 2 or len(X) < 3:
        return None
    xy = PCA(n_components=2, random_state=0).fit_transform(X)
    labs = pd.Series(list(labels)).astype(str)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for i, lab in enumerate(sorted(labs.unique())):
        m = labs == lab
        ax.scatter(xy[m, 0], xy[m, 1], s=28, alpha=0.75, color=PALETTE[i % len(PALETTE)], label=lab)
    ax.legend(frameon=False, fontsize=8, title="label")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    tidy(ax)
    ax.grid(color=GRID, lw=0.5)
    fig.tight_layout()
    return save(fig, path, show=show)


def group_compare_dumbbell(
    compare: pd.DataFrame,
    *,
    label_col: str,
    group_a: str,
    group_b: str,
    path: str | Path | None = None,
    show: bool = True,
    title: str = "Document-weighted shares",
):
    """Dumbbell chart: two groups' percentages with bootstrap intervals."""
    plt = _plt()
    a_pct, b_pct = f"{group_a}_pct", f"{group_b}_pct"
    a_lo, a_hi = f"{group_a}_lo", f"{group_a}_hi"
    b_lo, b_hi = f"{group_b}_lo", f"{group_b}_hi"
    df = compare.sort_values(a_pct, ascending=True).reset_index(drop=True)
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(df) + 1.6))
    for i in range(len(df)):
        r = df.iloc[i]
        ax.plot([r[a_pct], r[b_pct]], [i, i], color=GRID, lw=2, zorder=1)
        if a_lo in df.columns:
            ax.plot([r[a_lo], r[a_hi]], [i - 0.12] * 2, color=PALETTE[0], lw=1.1, alpha=0.7)
        if b_lo in df.columns:
            ax.plot([r[b_lo], r[b_hi]], [i + 0.12] * 2, color=PALETTE[1], lw=1.1, alpha=0.7)
        ax.scatter([r[a_pct]], [i], color=PALETTE[0], s=36, zorder=2, label=group_a if i == 0 else None)
        ax.scatter([r[b_pct]], [i], color=PALETTE[1], s=36, zorder=2, label=group_b if i == 0 else None)
    ax.set_yticks(y)
    ax.set_yticklabels(df[label_col].astype(str))
    ax.set_xlabel("Share of document-level mass (%)")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)


def variance_share_bars(
    shares: pd.DataFrame,
    *,
    path: str | Path | None = None,
    show: bool = True,
):
    """Bar chart of multiverse variance shares by analytic dimension."""
    plt = _plt()
    df = shares.copy()
    # expect dimension + share columns
    dim_col = "dimension" if "dimension" in df.columns else df.columns[0]
    if "variance_share" in df.columns:
        share_col = "variance_share"
    elif "share" in df.columns:
        share_col = "share"
    else:
        share_col = [c for c in df.columns if c != dim_col][0]
    df = df.sort_values(share_col, ascending=True)
    fig, ax = plt.subplots(figsize=(6.5, 0.45 * len(df) + 1.4))
    ax.barh(df[dim_col].astype(str), df[share_col], color=PALETTE[3])
    ax.set_xlabel("Variance share")
    ax.set_title("Multiverse variance decomposition", loc="left", color=INK, fontsize=11)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)


def multiverse_metric_strip(
    results: pd.DataFrame,
    metric: str,
    *,
    colour_by: str | None = None,
    path: str | Path | None = None,
    show: bool = True,
):
    """Strip / swarm of ℓ across multiverse configurations."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7, 2.8))
    y = np.zeros(len(results)) + np.random.default_rng(0).uniform(-0.12, 0.12, len(results))
    if colour_by and colour_by in results.columns:
        for i, (lab, sub) in enumerate(results.groupby(colour_by)):
            m = results[colour_by] == lab
            ax.scatter(
                results.loc[m, metric],
                y[m.to_numpy()],
                s=40,
                alpha=0.8,
                color=PALETTE[i % len(PALETTE)],
                label=str(lab),
            )
        ax.legend(frameon=False, fontsize=8, title=colour_by)
    else:
        ax.scatter(results[metric], y, s=40, alpha=0.8, color=PALETTE[0])
    ax.axvline(results[metric].median(), color=INK, lw=1.2)
    ax.set_yticks([])
    ax.set_xlabel(metric)
    ax.set_title("Headline metric across the multiverse", loc="left", color=INK, fontsize=11)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)
