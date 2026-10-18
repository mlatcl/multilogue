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


def _clip_label(text: str | None, n: int = 34) -> str:
    """Truncate catalogue names so legends / titles cannot explode figure width.

    Jupyter's inline backend saves with ``bbox_inches='tight'``. A legend entry
    that embeds a full LLM topic label can make the PNG thousands of pixels
    wide; the notebook then scales that image to the cell width and the scatter
    collapses. Keep decorative strings short; put the full name in annotations
    only when clipped.
    """
    s = str(text or "").strip() or "—"
    if len(s) <= n:
        return s
    return s[: max(n - 1, 1)] + "…"


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


def _component_local_plane(
    X: np.ndarray,
    weights: np.ndarray,
    component_fit: dict | None,
    *,
    q_viz: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int] | None:
    """Return ``(mu, U, scales, q_model)`` for a Bishop–Tipping local plane.

    ``U`` is ``(d, q_viz)`` orthonormal. ``scales`` are semi-axis lengths in
    that plane (``sqrt(lambda)`` along each column of ``U``) so the panel can
    draw the local PPCA pancake / principal-axis shape.

    Prefer the fitted component's ``U_q``. Bishop & Tipping fix the
    visualisation latent dim at 2; if ML truncation left ``q < 2``, pad with
    the next weighted singular vectors.
    """
    X = np.asarray(X, float)
    w = np.asarray(weights, float).ravel()
    if X.ndim != 2 or w.shape[0] != X.shape[0] or float(w.sum()) <= 0:
        return None
    mu = None
    U_model = None
    lam_model = None
    q_model = 0
    if component_fit is not None:
        mu = np.asarray(component_fit.get("mu"), float).ravel()
        U_model = np.asarray(component_fit.get("U_q"), float)
        lam_model = np.asarray(component_fit.get("lambdas_q"), float).ravel()
        q_model = int(component_fit.get("q", U_model.shape[1] if U_model.ndim == 2 else 0))
        if mu.shape[0] != X.shape[1]:
            mu = None
            U_model = None
            lam_model = None
            q_model = 0
    if mu is None:
        mu = (w[:, None] * X).sum(axis=0) / float(w.sum())
    Xc = X - mu
    need = int(q_viz)
    cols: list[np.ndarray] = []
    lams: list[float] = []
    if U_model is not None and U_model.ndim == 2 and U_model.shape[0] == X.shape[1]:
        for j in range(min(U_model.shape[1], need)):
            cols.append(U_model[:, j])
            if lam_model is not None and j < len(lam_model):
                lams.append(float(max(lam_model[j], 0.0)))
            else:
                lams.append(0.0)
    if len(cols) < need:
        sw = np.sqrt(np.clip(w, 0.0, None))
        Xw = sw[:, None] * Xc
        _, s, Vt = np.linalg.svd(Xw, full_matrices=False)
        w_sum = float(w.sum())
        eig = (s ** 2) / w_sum if w_sum > 0 else s ** 2
        for i, row in enumerate(Vt):
            if len(cols) >= need:
                break
            v = row.astype(float)
            if any(abs(float(np.dot(v, c))) > 0.99 for c in cols):
                continue
            cols.append(v)
            lams.append(float(max(eig[i], 0.0)) if i < len(eig) else 0.0)
    if not cols:
        return None
    while len(cols) < need:
        cols.append(np.zeros(X.shape[1]))
        lams.append(0.0)
    U = np.column_stack(cols[:need])
    Q, _ = np.linalg.qr(U)
    # Recompute variances along the orthonormalised plane axes
    sw = np.sqrt(np.clip(w, 0.0, None))
    Xw = sw[:, None] * Xc
    scales = np.zeros(need, dtype=float)
    w_sum = float(w.sum())
    for j in range(need):
        proj = Xw @ Q[:, j]
        var = float((proj ** 2).sum() / w_sum) if w_sum > 0 else 0.0
        # Prefer model eigenvalue when the axis still aligns with U_q
        if j < len(lams) and lams[j] > 0 and U_model is not None and j < U_model.shape[1]:
            if abs(float(np.dot(Q[:, j], U_model[:, j]))) > 0.9:
                var = max(var, lams[j])
        scales[j] = float(np.sqrt(max(var, 0.0)))
    return mu, Q[:, :need], scales, q_model


def topic_fit_view(
    embeddings: np.ndarray,
    responsibilities: np.ndarray,
    means: np.ndarray | None = None,
    *,
    focus: int,
    component_fits: list | None = None,
    title: str | None = None,
    path: str | Path | None = None,
    show: bool = True,
    sigma2: float | None = None,
):
    """Local Bishop–Tipping plane for one mixture component (CIP-0009).

    *Every* phrase is projected onto the selected component's ``U_q`` plane;
    ink density (alpha) is soft mass on ``focus`` — points that do not belong
    appear faint, as in Bishop & Tipping (TPAMI 1998). The local PPCA shape
    is drawn as a 1-SD ellipse in that plane plus principal-axis ticks.

    Parameters
    ----------
    focus :
        Component index whose local ``U_q`` defines the panel axes.
    component_fits :
        Per-component PPCA dicts from :func:`multilogue.mppca.mppca_fit`
        (``fit["component_fits"]``). If omitted, the plane is the top-2
        weighted SVD under ``R[:, focus]``.
    sigma2 :
        Optional topic noise; enlarges the ellipse by ``sqrt(sigma2)`` in
        isotropic residual directions when provided via ``component_fits``
        parent fit (passed explicitly if known).
    """
    plt = _plt()
    from matplotlib.patches import Ellipse

    X = np.asarray(embeddings, float)
    R = np.asarray(responsibilities, float)
    focus = int(focus)
    if X.ndim != 2 or len(X) < 2 or R.ndim != 2 or R.shape[0] != len(X):
        return None
    if focus < 0 or focus >= R.shape[1]:
        return None
    if not np.isfinite(X).all() or not np.isfinite(R).all():
        return None

    cf = None
    if component_fits is not None and 0 <= focus < len(component_fits):
        cf = component_fits[focus]
    plane = _component_local_plane(X, R[:, focus], cf, q_viz=2)
    if plane is None:
        return None
    mu, U, scales, q_model = plane
    xy = (X - mu) @ U
    if not np.isfinite(xy).all():
        return None

    mass = np.clip(R[:, focus], 0.0, 1.0)
    # Floor so near-zero mass still leaves a ghost of non-members (Bishop ink)
    alpha = np.clip(0.04 + 0.92 * mass, 0.04, 1.0)

    if title is None:
        title = f"Topic {focus} — local U_q (model q={q_model})"

    fig, ax = plt.subplots(figsize=(6.5, 5))
    # All points: ink density ∝ responsibility (non-members stay visible but faint)
    order = np.argsort(mass)  # draw high-mass on top
    ax.scatter(
        xy[order, 0],
        xy[order, 1],
        s=18 + 36 * mass[order],
        c=INK,
        alpha=alpha[order],
        edgecolors="none",
        zorder=2,
    )
    # Local PPCA shape: 1-SD ellipse in the U_q plane + axis ticks
    s0 = float(scales[0]) if len(scales) > 0 else 0.0
    s1 = float(scales[1]) if len(scales) > 1 else 0.0
    if sigma2 is not None and sigma2 > 0:
        # Residual isotropic noise also contributes in-plane
        s0 = float(np.sqrt(s0 ** 2 + float(sigma2)))
        s1 = float(np.sqrt(s1 ** 2 + float(sigma2)))
    if s0 > 0 or s1 > 0:
        ell = Ellipse(
            (0.0, 0.0),
            width=2.0 * max(s0, 1e-9),
            height=2.0 * max(s1, 1e-9),
            facecolor="none",
            edgecolor=PALETTE[focus % len(PALETTE)],
            linewidth=1.8,
            linestyle="-",
            zorder=3,
            label="1-SD local U_q",
        )
        ax.add_patch(ell)
        # Principal-axis ticks (shape of the local plane)
        ax.plot([-s0, s0], [0.0, 0.0], color=PALETTE[focus % len(PALETTE)], lw=1.4, zorder=3)
        ax.plot([0.0, 0.0], [-s1, s1], color=PALETTE[focus % len(PALETTE)], lw=1.4, zorder=3)
    # Component mean is the origin of this latent plane
    ax.scatter(
        [0.0],
        [0.0],
        s=140,
        marker="X",
        c=[PALETTE[focus % len(PALETTE)]],
        edgecolors=INK,
        linewidths=0.9,
        zorder=5,
        label=f"μ_{focus}",
    )
    # Sibling means: use *raw* component mus (same space as U_q), not L2-renormed
    # catalogue means. In-plane distance is often small — separation usually lives
    # in directions orthogonal to this topic's plane; annotate out-of-plane ‖r⊥‖.
    raw_means = None
    if component_fits is not None:
        try:
            raw_means = np.vstack(
                [np.asarray(cf["mu"], float).ravel() for cf in component_fits]
            )
        except (KeyError, ValueError, TypeError):
            raw_means = None
    if raw_means is None and means is not None:
        raw_means = np.asarray(means, float)
    if raw_means is not None and raw_means.ndim == 2 and raw_means.shape[1] == X.shape[1]:
        for j in range(len(raw_means)):
            if j == focus:
                continue
            delta = raw_means[j] - mu
            pj = delta @ U
            # Residual orthogonal to the local plane
            recon = U @ pj
            perp = float(np.linalg.norm(delta - recon))
            if np.isfinite(pj).all():
                ax.scatter(
                    [pj[0]],
                    [pj[1]],
                    s=70,
                    marker="+",
                    c=[PALETTE[j % len(PALETTE)]],
                    linewidths=1.2,
                    zorder=4,
                    label=f"μ_{j} (⊥{perp:.2f})",
                )
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(frameon=False, fontsize=8, loc="best")
    ax.set_xlabel("local PC1 (U_q)")
    ax.set_ylabel("local PC2 (U_q)")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    tidy(ax)
    ax.grid(color=GRID, lw=0.5)
    fig.tight_layout()
    return save(fig, path, show=show)


def _ppca_cov(component_fit: dict, sigma2: float) -> np.ndarray:
    """Ambient covariance for a PPCA component: ``U diag(λ) Uᵀ + σ² I``."""
    mu = np.asarray(component_fit["mu"], float).ravel()
    d = int(mu.shape[0])
    Cov = np.eye(d) * float(max(sigma2, 0.0))
    U = np.asarray(component_fit.get("U_q"), float)
    lam = np.asarray(component_fit.get("lambdas_q"), float).ravel()
    if U.ndim == 2 and U.shape[0] == d and U.size and lam.size:
        q = min(U.shape[1], len(lam))
        if q > 0:
            Cov = Cov + (U[:, :q] * lam[:q]) @ U[:, :q].T
    return Cov


def _ellipse_from_plane_cov(
    center_xy: np.ndarray,
    C2: np.ndarray,
    *,
    color: str,
    label: str | None = None,
    zorder: int = 4,
    linestyle: str = "--",
):
    """1-SD ellipse from a 2×2 in-plane covariance."""
    from matplotlib.patches import Ellipse

    evals, evecs = np.linalg.eigh(np.asarray(C2, float))
    evals = np.clip(evals, 0.0, None)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    width = 2.0 * float(np.sqrt(max(evals[0], 1e-18)))
    height = 2.0 * float(np.sqrt(max(evals[1], 1e-18)))
    angle = float(np.degrees(np.arctan2(evecs[1, 0], evecs[0, 0])))
    return Ellipse(
        (float(center_xy[0]), float(center_xy[1])),
        width=width,
        height=height,
        angle=angle,
        facecolor="none",
        edgecolor=color,
        linewidth=1.8,
        linestyle=linestyle,
        zorder=zorder,
        label=label,
    )


def _equal_plane_frame(
    ax,
    xy: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    anchors: Sequence[np.ndarray] | None = None,
    pad_frac: float = 0.2,
    anchor_cap: float = 2.0,
) -> None:
    """Square data window from the soft cloud (not decorative ellipses).

    Framing rules:
    - Base the window on mass-weighted point percentiles (+ origin).
    - Optionally pull in nearby anchors (means, merged 1-SD radii), but never
      more than ``anchor_cap`` × the mass half-span — distant sources stay
      off-screen rather than zooming the cloud to a speck.
    - Never let decorative source ellipses set the limits (caller must omit them).

    Uses ``set_box_aspect(1)`` + equal ``xlim``/``ylim`` spans so circles stay
    round without ``set_aspect(..., adjustable='datalim')``, which warns and
    ignores the limits we just set.
    """
    xy = np.asarray(xy, float)
    if xy.ndim != 2 or xy.shape[0] == 0 or xy.shape[1] < 2:
        return
    pts = xy[:, :2]
    if weights is not None:
        w = np.asarray(weights, float).ravel()
        if w.shape[0] == len(pts):
            thr = max(float(np.quantile(w, 0.75)) * 0.02, 1e-9)
            mask = w >= thr
            if int(mask.sum()) >= 8:
                pts = pts[mask]
    lo = np.percentile(pts, 2, axis=0)
    hi = np.percentile(pts, 98, axis=0)
    lo = np.minimum(lo, 0.0)
    hi = np.maximum(hi, 0.0)
    mass_span = np.maximum(hi - lo, 1e-9)
    mid = 0.5 * (lo + hi)
    mass_half = 0.5 * float(mass_span.max()) * (1.0 + float(pad_frac))
    if mass_half < 1e-6:
        mass_half = 1.0
    half = mass_half
    if anchors:
        max_r = float(anchor_cap) * mass_half
        for a in anchors:
            p = np.asarray(a, float).ravel()
            if p.size < 2 or not np.isfinite(p[:2]).all():
                continue
            need = float(np.max(np.abs(p[:2] - mid)))
            if need <= max_r:
                half = max(half, need * (1.0 + float(pad_frac)))
    ax.set_xlim(float(mid[0] - half), float(mid[0] + half))
    ax.set_ylim(float(mid[1] - half), float(mid[1] + half))
    ax.set_box_aspect(1)


def proposed_merge_view(
    embeddings: np.ndarray,
    *,
    merged_mass: np.ndarray,
    merged_component_fit: dict,
    source_component_fits: Sequence[dict],
    source_labels: Sequence[str] | None = None,
    merged_label: str | None = None,
    sigma2: float = 0.0,
    title: str | None = None,
    path: str | Path | None = None,
    show: bool = True,
):
    """Proposed merge: originals in the *merged* soft-mass ``U_q`` plane.

    Ink follows the summed responsibility of the topics being merged. The
    plane is the local PPCA of that combined mass (the updated leaf). Each
    source topic is drawn as a dashed 1-SD ellipse + mean with its catalogue
    label; the merged mean is a solid marker at the origin of this plane.
    """
    plt = _plt()

    X = np.asarray(embeddings, float)
    mass = np.asarray(merged_mass, float).ravel()
    if X.ndim != 2 or len(X) < 2 or mass.shape[0] != len(X):
        return None
    if not source_component_fits:
        return None
    if not np.isfinite(X).all() or not np.isfinite(mass).all():
        return None

    plane = _component_local_plane(X, mass, merged_component_fit, q_viz=2)
    if plane is None:
        return None
    mu, U, _scales, q_model = plane
    xy = (X - mu) @ U
    if not np.isfinite(xy).all():
        return None

    alpha = np.clip(0.04 + 0.92 * np.clip(mass, 0.0, 1.0), 0.04, 1.0)
    n_src = len(source_component_fits)
    merge_name = merged_label or "merged"
    if title is None:
        title = (
            f"Proposed merge of {n_src} topics → "
            f"«{_clip_label(merge_name, 40)}» (merged U_q, q={q_model})"
        )

    fig, ax = plt.subplots(figsize=(6.5, 5))
    order = np.argsort(mass)
    ax.scatter(
        xy[order, 0],
        xy[order, 1],
        s=18 + 36 * np.clip(mass[order], 0.0, 1.0),
        c=INK,
        alpha=alpha[order],
        edgecolors="none",
        zorder=2,
    )
    # Merged mean at origin of this plane
    ax.scatter(
        [0.0],
        [0.0],
        s=120,
        marker="X",
        c=[MUTED],
        edgecolors=INK,
        linewidths=0.9,
        zorder=5,
        label="merged μ",
    )
    Cov_m = _ppca_cov(merged_component_fit, float(sigma2))
    C2_m = U.T @ Cov_m @ U
    ax.add_patch(
        _ellipse_from_plane_cov(
            np.zeros(2),
            C2_m,
            color=MUTED,
            label="1-SD merged",
            zorder=3,
            linestyle="-",
        )
    )
    # Frame anchors: merged 1-SD extents (not source ellipses — those can explode)
    anchors: list[np.ndarray] = [np.zeros(2)]
    evals_m = np.clip(np.linalg.eigvalsh(np.asarray(C2_m, float)), 0.0, None)
    r_m = float(np.sqrt(max(float(evals_m.max()), 0.0)))
    if r_m > 0:
        anchors.extend(
            [
                np.array([r_m, 0.0]),
                np.array([-r_m, 0.0]),
                np.array([0.0, r_m]),
                np.array([0.0, -r_m]),
            ]
        )

    for j, cf in enumerate(source_component_fits):
        color = PALETTE[j % len(PALETTE)]
        mu_s = np.asarray(cf["mu"], float).ravel()
        center = (mu_s - mu) @ U
        Cov = _ppca_cov(cf, float(sigma2))
        C2 = U.T @ Cov @ U
        name = (
            str(source_labels[j])
            if source_labels is not None and j < len(source_labels)
            else f"source {j}"
        )
        short = _clip_label(name, 28)
        # No legend labels here — full LLM names blow out Jupyter's tight bbox
        ax.add_patch(
            _ellipse_from_plane_cov(
                center, C2, color=color, label=None, zorder=4
            )
        )
        ax.scatter(
            [center[0]],
            [center[1]],
            s=110,
            marker="+",
            c=[color],
            linewidths=1.4,
            zorder=5,
        )
        if np.isfinite(center).all():
            anchors.append(np.asarray(center, float).ravel()[:2])
            ax.annotate(
                short,
                (float(center[0]), float(center[1])),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
                color=color,
                zorder=6,
            )

    _equal_plane_frame(ax, xy, weights=mass, anchors=anchors)
    ax.legend(frameon=False, fontsize=8, loc="best")
    ax.set_xlabel("merged local PC1 (U_q)")
    ax.set_ylabel("merged local PC2 (U_q)")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    tidy(ax)
    ax.grid(color=GRID, lw=0.5)
    fig.tight_layout()
    return save(fig, path, show=show)


def proposed_split_view(
    embeddings: np.ndarray,
    *,
    parent_mass: np.ndarray,
    parent_component_fit: dict,
    child_component_fits: Sequence[dict],
    child_labels: Sequence[str] | None = None,
    parent_label: str | None = None,
    sigma2: float = 0.0,
    title: str | None = None,
    path: str | Path | None = None,
    show: bool = True,
):
    """Proposed split: child means + local cov in the *parent* ``U_q`` plane.

    Geometry stays in the basis of the topic that was split. Child PPCA
    covariances are projected into that plane as dashed 1-SD ellipses. Point
    ink follows parent soft mass (the bag being partitioned).
    """
    plt = _plt()

    X = np.asarray(embeddings, float)
    mass = np.asarray(parent_mass, float).ravel()
    if X.ndim != 2 or len(X) < 2 or mass.shape[0] != len(X):
        return None
    if not child_component_fits:
        return None
    if not np.isfinite(X).all() or not np.isfinite(mass).all():
        return None

    plane = _component_local_plane(X, mass, parent_component_fit, q_viz=2)
    if plane is None:
        return None
    mu, U, _scales, q_model = plane
    xy = (X - mu) @ U
    if not np.isfinite(xy).all():
        return None

    alpha = np.clip(0.04 + 0.92 * np.clip(mass, 0.0, 1.0), 0.04, 1.0)
    parent_name = parent_label or "parent"
    if title is None:
        title = (
            f"Proposed split of «{_clip_label(parent_name, 40)}» "
            f"— parent U_q (q={q_model})"
        )

    fig, ax = plt.subplots(figsize=(6.5, 5))
    order = np.argsort(mass)
    ax.scatter(
        xy[order, 0],
        xy[order, 1],
        s=18 + 36 * np.clip(mass[order], 0.0, 1.0),
        c=INK,
        alpha=alpha[order],
        edgecolors="none",
        zorder=2,
    )
    # Parent mean at origin of this plane
    ax.scatter(
        [0.0],
        [0.0],
        s=100,
        marker="x",
        c=[MUTED],
        linewidths=1.2,
        zorder=3,
        label="parent μ",
    )

    anchors: list[np.ndarray] = [np.zeros(2)]
    for j, cf in enumerate(child_component_fits):
        color = PALETTE[j % len(PALETTE)]
        mu_c = np.asarray(cf["mu"], float).ravel()
        center = (mu_c - mu) @ U
        Cov = _ppca_cov(cf, float(sigma2))
        C2 = U.T @ Cov @ U
        name = None
        if child_labels is not None and j < len(child_labels):
            name = str(child_labels[j])
        if not name:
            name = f"child {j}"
        short = _clip_label(name, 28)
        ax.add_patch(
            _ellipse_from_plane_cov(
                center, C2, color=color, label=None, zorder=4
            )
        )
        ax.scatter(
            [center[0]],
            [center[1]],
            s=140,
            marker="X",
            c=[color],
            edgecolors=INK,
            linewidths=0.9,
            zorder=5,
        )
        if np.isfinite(center).all():
            anchors.append(np.asarray(center, float).ravel()[:2])
            ax.annotate(
                short,
                (float(center[0]), float(center[1])),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
                color=color,
                zorder=6,
            )

    _equal_plane_frame(ax, xy, weights=mass, anchors=anchors)
    ax.legend(frameon=False, fontsize=8, loc="best")
    ax.set_xlabel("parent local PC1 (U_q)")
    ax.set_ylabel("parent local PC2 (U_q)")
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


def sigma2_stability_curve(
    curve: pd.DataFrame,
    *,
    sigma2_best: float | None = None,
    path: str | Path | None = None,
    show: bool = True,
):
    """Plot mean EMD and effective support vs σ² (log-x)."""
    plt = _plt()
    df = curve.sort_values("sigma2")
    fig, ax1 = plt.subplots(figsize=(7.2, 3.4))
    ax1.plot(df["sigma2"], df["mean_emd"], color=PALETTE[0], lw=1.8, label="mean EMD")
    ax1.set_xscale("log")
    ax1.set_xlabel("σ²")
    ax1.set_ylabel("Mean pairwise EMD", color=PALETTE[0])
    ax1.tick_params(axis="y", colors=PALETTE[0])
    ax2 = ax1.twinx()
    ax2.plot(
        df["sigma2"],
        df["mean_eff_support"],
        color=PALETTE[1],
        lw=1.5,
        ls="--",
        label="mean eff. support",
    )
    ax2.set_ylabel("Mean effective support", color=PALETTE[1])
    ax2.tick_params(axis="y", colors=PALETTE[1])
    if sigma2_best is not None:
        ax1.axvline(sigma2_best, color=INK, lw=1.2, label=f"σ²*={sigma2_best:.3g}")
    ax1.set_title("σ² stability sweep", loc="left", color=INK, fontsize=11)
    tidy(ax1)
    fig.tight_layout()
    return save(fig, path, show=show)


def mixture_weight_heatmap(
    W: np.ndarray,
    lens_names: Sequence[str],
    *,
    path: str | Path | None = None,
    show: bool = True,
):
    """Heatmap of cluster × lens mixture weights."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(0.55 * max(len(lens_names), 4) + 2.5, 0.35 * W.shape[0] + 1.8))
    im = ax.imshow(W, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(lens_names)))
    ax.set_xticklabels(list(lens_names), rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(W.shape[0]))
    ax.set_yticklabels([f"c{i}" for i in range(W.shape[0])], fontsize=8)
    ax.set_xlabel("Lens")
    ax.set_ylabel("Cluster")
    ax.set_title("Soft mixture weights", loc="left", color=INK, fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return save(fig, path, show=show)


def doc_mds_scatter(
    coords: np.ndarray,
    groups: Sequence[str],
    *,
    title: str = "Document EMD → classical MDS",
    path: str | Path | None = None,
    show: bool = True,
):
    """Scatter MDS coordinates coloured by group."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    groups = np.asarray(groups)
    for i, g in enumerate(sorted(set(groups.tolist()))):
        m = groups == g
        ax.scatter(
            coords[m, 0],
            coords[m, 1],
            label=str(g),
            color=PALETTE[i % len(PALETTE)],
            s=48,
            alpha=0.85,
        )
    ax.set_xlabel("MDS 1")
    ax.set_ylabel("MDS 2")
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    tidy(ax)
    fig.tight_layout()
    return save(fig, path, show=show)
