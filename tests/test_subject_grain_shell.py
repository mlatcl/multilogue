"""CIP-0009 Layer B — SubjectGrainShell state machine (no display required)."""

from pathlib import Path

import numpy as np
import pytest

from multilogue.mppca import mppca_fit
from multilogue.subject_grain_shell import SubjectGrainShell, ipywidgets_available


def _planted(k: int = 3, n_per: int = 30, d: int = 10, seed: int = 0):
    rng = np.random.default_rng(seed)
    means = np.zeros((k, d))
    for j in range(k):
        means[j, j] = 3.5
    Xs = []
    for j in range(k):
        cov = np.eye(d) * 0.08
        Xs.append(rng.multivariate_normal(means[j], cov, size=n_per))
    X = np.vstack(Xs)
    perm = rng.permutation(len(X))
    X = X[perm]
    phrases = [f"phrase-{i}" for i in range(len(X))]
    fit = mppca_fit(X, k=k, sigma2=0.12, seed=seed, max_iter=25)
    return X, fit, phrases


def _fake_label_work(prefix: str = "Named"):
    def work(cu: dict) -> dict:
        return {
            "label": f"{prefix} {cu['cluster']}",
            "description": f"desc {cu['cluster']}",
        }

    return work


def test_import_multilogue_without_requiring_ipywidgets():
    """Core package + shell module import must not hard-require ipywidgets."""
    import multilogue
    import multilogue.subject_grain_shell as sgs

    assert multilogue.__version__
    assert hasattr(sgs, "SubjectGrainShell")
    # Construction does not import ipywidgets
    X, fit, phrases = _planted(seed=1)
    shell = SubjectGrainShell(X, fit, phrases, seed=1)
    assert shell.k == 3


def test_merge_split_undo_dirty_lock(tmp_path: Path):
    X, fit, phrases = _planted(seed=2)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "A", 1: "B", 2: "C"},
        seed=2,
        label_work=_fake_label_work(),
    )
    assert shell.dirty == set()
    shell.merge([0, 1])
    assert shell.k == 2
    assert shell.dirty  # merged leaf dirty
    assert "unnamed / stale" in shell.labels.values()
    # Geometry refresh path does not need LLM
    cat = shell.catalogue()
    assert "dirty" in cat.columns
    assert cat["dirty"].any()

    shell.split(1)
    assert shell.k == 3
    assert len(shell.dirty) >= 2

    assert shell.undo() is True  # undo split
    assert shell.k == 2
    assert shell.undo() is True  # undo merge
    assert shell.k == 3
    assert shell.labels[0] == "A"
    assert shell.undo() is False  # empty

    shell.merge([1, 2])
    named = shell.name_dirty()
    assert named
    assert shell.dirty == set()
    for c in named:
        assert shell.labels[c].startswith("Named")

    lock_path = tmp_path / "subject_grain_lock.json"
    artefact = shell.lock(path=lock_path, k_multiverse="hold")
    assert artefact["primary_k"] == shell.k
    assert artefact["k_multiverse"] == [shell.k]
    assert lock_path.exists()
    assert shell.locked is not None


def test_name_dirty_only_touches_dirty_ids():
    X, fit, phrases = _planted(seed=3)
    calls: list[int] = []

    def work(cu: dict) -> dict:
        calls.append(int(cu["cluster"]))
        return {"label": f"L{cu['cluster']}", "description": ""}

    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "keep0", 1: "keep1", 2: "keep2"},
        seed=3,
        label_work=work,
    )
    shell.merge([0, 1])
    dirty_before = set(shell.dirty)
    # Topic that survived merge (old 2 → new 0) should keep "keep2"
    assert shell.labels[0] == "keep2"
    assert 0 not in dirty_before
    shell.name_dirty()
    assert set(calls) == dirty_before
    assert shell.labels[0] == "keep2"  # never re-labelled
    assert shell.dirty == set()


def test_name_dirty_requires_label_work():
    X, fit, phrases = _planted(seed=4)
    shell = SubjectGrainShell(X, fit, phrases, seed=4)
    shell.merge([0, 1])
    with pytest.raises(ValueError, match="label_work"):
        shell.name_dirty()


def test_name_after_action_toggle():
    X, fit, phrases = _planted(seed=5)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        seed=5,
        label_work=_fake_label_work("Auto"),
        name_after_action=True,
    )
    shell.merge([0, 1])
    assert shell.dirty == set()
    assert any(v.startswith("Auto") for v in shell.labels.values())


def test_widgets_optional():
    X, fit, phrases = _planted(seed=6)
    shell = SubjectGrainShell(X, fit, phrases, seed=6)
    if not ipywidgets_available():
        with pytest.raises(ImportError, match="ipywidgets"):
            shell.widgets()
    else:
        # Construct without displaying (no Jupyter frontend needed for object build)
        ui = shell.widgets()
        assert ui is not None
