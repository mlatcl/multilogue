"""CIP-0009 Layer A + subject-grain lock artefact."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from multilogue.experiment import run_formats_complexity_demo
from multilogue.mppca import mppca_fit, responsibilities_to_labels
from multilogue.subject_grain import (
    fit_fingerprint,
    lock_subject_grain,
    propose_merge,
    propose_split,
    resolve_k_multiverse,
    subject_grain_diagnostics,
    topic_catalogue,
)


def _planted_blobs(
    *,
    n_per: int = 35,
    d: int = 12,
    seed: int = 0,
    k: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    means = np.zeros((k, d))
    for j in range(k):
        means[j, j] = 3.5
    Xs, ys = [], []
    for j in range(k):
        cov = np.eye(d) * 0.08
        Xs.append(rng.multivariate_normal(means[j], cov, size=n_per))
        ys.append(np.full(n_per, j, dtype=int))
    X = np.vstack(Xs)
    y = np.concatenate(ys)
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


def test_resolve_k_multiverse_hold_and_pm1():
    assert resolve_k_multiverse(10, "hold") == [10]
    assert resolve_k_multiverse(10, None) == [10]
    assert resolve_k_multiverse(10, "pm1") == [9, 10, 11]
    assert resolve_k_multiverse(2, "pm1") == [2, 3]
    assert resolve_k_multiverse(8, [5, 8, 12]) == [5, 8, 12]


def test_lock_subject_grain_fields():
    X, _ = _planted_blobs(seed=1)
    fit = mppca_fit(X, k=3, sigma2=0.1, seed=1, max_iter=20)
    lock = lock_subject_grain(
        primary_k=3,
        responsibilities=fit["responsibilities"],
        means=fit["means"],
        k_multiverse="hold",
        sigma2=fit["sigma2"],
        diagnostics=subject_grain_diagnostics(fit),
    )
    assert lock["primary_k"] == 3
    assert lock["k_multiverse"] == [3]
    assert lock["fit_fingerprint"]
    assert lock["n_topics"] == 3
    assert lock["sigma2"] == pytest.approx(0.1)


def test_fit_fingerprint_stable():
    X, _ = _planted_blobs(seed=2)
    fit = mppca_fit(X, k=3, sigma2=0.1, seed=2, max_iter=15)
    a = fit_fingerprint(fit["responsibilities"], fit["means"])
    b = fit_fingerprint(fit["responsibilities"], fit["means"])
    assert a == b


def test_propose_merge_reduces_k_and_marks_dirty():
    X, _ = _planted_blobs(seed=3, k=3)
    fit = mppca_fit(X, k=3, sigma2=0.12, seed=3, max_iter=25)
    out = propose_merge(X, fit, [0, 1], seed=3)
    assert out["fit"]["k"] == 2
    assert out["fit"]["responsibilities"].shape == (X.shape[0], 2)
    np.testing.assert_allclose(out["fit"]["responsibilities"].sum(axis=1), 1.0, atol=1e-6)
    assert out["dirty"] == [1]  # merged leaf is last index
    assert out["history_entry"]["action"] == "merge"


def test_propose_split_increases_k():
    X, y = _planted_blobs(seed=4, k=2, n_per=40)
    fit = mppca_fit(X, k=2, sigma2=0.12, seed=4, max_iter=30)
    # Split the larger MAP topic
    labels = responsibilities_to_labels(fit["responsibilities"])
    sizes = np.bincount(labels, minlength=2)
    big = int(np.argmax(sizes))
    out = propose_split(X, fit, big, n_children=2, seed=4)
    assert out["fit"]["k"] == 3
    assert out["fit"]["responsibilities"].shape == (X.shape[0], 3)
    np.testing.assert_allclose(out["fit"]["responsibilities"].sum(axis=1), 1.0, atol=1e-6)
    assert len(out["dirty"]) == 2
    assert out["history_entry"]["action"] == "split"


def test_merge_then_split_recovers_separable_structure():
    """Planted 3 blobs: merge 0+1 → 2 topics; split merged → can recover 3 MAP topics."""
    X, y_true = _planted_blobs(seed=5, k=3, n_per=45)
    fit = mppca_fit(X, k=3, sigma2=0.1, seed=5, max_iter=40)
    merged = propose_merge(X, fit, [0, 1], seed=5)
    assert merged["fit"]["k"] == 2
    # Split the merged leaf (index 1)
    split = propose_split(X, merged["fit"], 1, n_children=2, seed=5)
    assert split["fit"]["k"] == 3
    pred = responsibilities_to_labels(split["fit"]["responsibilities"])
    n_map = len(set(pred.tolist()))
    assert n_map >= 2  # at least separated; ideally 3
    assert float(split["fit"]["responsibilities"].max(axis=1).mean()) > 0.5


def test_topic_catalogue_deterministic_and_dirty_flag():
    X, _ = _planted_blobs(seed=6, k=3)
    fit = mppca_fit(X, k=3, sigma2=0.1, seed=6, max_iter=20)
    phrases = [f"phrase-{i}" for i in range(len(X))]
    cat_a = topic_catalogue(phrases, fit["responsibilities"], dirty=[1], seed=6)
    cat_b = topic_catalogue(phrases, fit["responsibilities"], dirty=[1], seed=6)
    assert list(cat_a["examples"]) == list(cat_b["examples"])
    assert bool(cat_a.loc[cat_a["topic"] == 1, "dirty"].iloc[0]) is True
    assert bool(cat_a.loc[cat_a["topic"] == 0, "dirty"].iloc[0]) is False


def test_topic_fit_view_finite(tmp_path: Path):
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    from multilogue.viz import topic_fit_view

    X, _ = _planted_blobs(seed=7, k=3)
    fit = mppca_fit(X, k=3, sigma2=0.1, seed=7, max_iter=20)
    path = tmp_path / "fit.png"
    out = topic_fit_view(
        X,
        fit["responsibilities"],
        fit["means"],
        path=path,
        show=False,
    )
    assert out is not None
    assert path.exists()


def test_formats_demo_writes_subject_grain_lock(tmp_path: Path):
    summary = run_formats_complexity_demo(
        tmp_path / "fmt",
        n_docs_per_group=3,
        units_per_doc=2,
        k=4,
        lens_runs=2,
        quiet=True,
    )
    lock = summary["subject_grain"]
    assert lock["primary_k"] == summary["k"]
    assert lock["k_multiverse"] == [summary["k"]]
    assert "k" not in summary["multiverse_dims"]
    assert (tmp_path / "fmt" / "run_manifest.json").exists()
    multi = pd.read_csv(tmp_path / "fmt" / "tables" / "multiverse_format_gap.csv")
    assert "k" not in multi.columns


def test_formats_demo_k_grid_one_factor_sweep(tmp_path: Path):
    summary = run_formats_complexity_demo(
        tmp_path / "fmt_k",
        n_docs_per_group=3,
        units_per_doc=2,
        k=4,
        lens_runs=2,
        quiet=True,
        k_grid=[3, 4, 5],
    )
    assert "k" not in summary["multiverse_dims"]
    sweep_path = tmp_path / "fmt_k" / "tables" / "resolution_k_sweep.csv"
    assert sweep_path.exists()
    sweep = pd.read_csv(sweep_path)
    assert set(sweep["k"].tolist()) <= {3, 4, 5}
    assert summary["resolution_k_sweep"] == len(sweep)
    # Lock records explicit levels from k_grid
    assert summary["subject_grain"]["k_multiverse"] == [3, 4, 5]
