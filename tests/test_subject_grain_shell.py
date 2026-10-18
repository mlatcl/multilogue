"""CIP-0009 Layer B — SubjectGrainShell state machine (no display required)."""

from pathlib import Path

import numpy as np
import pytest

from multilogue.mppca import mppca_fit
from multilogue.subject_grain import initial_assess_fit
from multilogue.subject_grain_shell import (
    SubjectGrainShell,
    ipywidgets_available,
    is_placeholder_label,
)


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
    assert shell.pending_proposal is not None
    assert shell.pending_proposal["kind"] == "merge"
    assert shell.pending_proposal["source_labels"] == ["A", "B"]
    # Merged leaf named via label_work on propose
    mid = int(shell.pending_proposal["merged_id"])
    assert shell.labels[mid].startswith("Named")
    assert shell.accept_proposal()
    assert shell.pending_proposal is None
    # Geometry refresh path does not need LLM
    cat = shell.catalogue()
    assert "dirty" in cat.columns

    shell.split(1)
    assert shell.k == 3
    assert shell.pending_proposal is not None
    assert shell.pending_proposal["kind"] == "split"
    # Children are LLM-named on split when label_work is set
    assert shell.pending_proposal["named"] is True
    assert shell.dirty == set()

    assert shell.undo() is True  # undo / reject split
    assert shell.k == 2
    assert shell.pending_proposal is None
    assert shell.undo() is True  # undo merge
    assert shell.k == 3
    assert shell.labels[0] == "A"
    assert shell.undo() is False  # empty

    shell.merge([1, 2])
    assert shell.pending_proposal["kind"] == "merge"
    shell.accept_proposal()
    named = shell.name_dirty()
    # may already be clean if auto-named on merge
    assert shell.dirty == set() or named is not None

    lock_path = tmp_path / "subject_grain_lock.json"
    artefact = shell.lock(path=lock_path, k_multiverse="hold")
    assert artefact["primary_k"] == shell.k
    assert artefact["k_multiverse"] == [shell.k]
    assert lock_path.exists()
    assert shell.locked is not None


def test_merge_preview_payload_and_view(tmp_path: Path):
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    X, fit, phrases = _planted(seed=11)
    shell = SubjectGrainShell(
        X, fit, phrases, labels={0: "Alpha", 1: "Beta", 2: "Gamma"}, seed=11
    )
    payload = shell.merge_preview_payload([0, 1])
    assert payload is not None
    assert len(payload["source_labels"]) == 2
    assert payload["source_labels"] == ["Alpha", "Beta"]
    from multilogue.viz import proposed_merge_view

    out = proposed_merge_view(
        X,
        merged_mass=payload["merged_mass"],
        merged_component_fit=payload["merged_component_fit"],
        source_component_fits=payload["source_component_fits"],
        source_labels=payload["source_labels"],
        merged_label=payload["merged_label"],
        path=tmp_path / "merge_preview.png",
        show=False,
    )
    assert out is not None
    # Selection preview via fit_view
    shell._merge_preview_ids = [0, 1]
    shell.fit_view(focus=0, path=tmp_path / "merge_fit.png", show=False)


def test_name_initial_seeds_llm_labels():
    X, fit, phrases = _planted(seed=8)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        seed=8,
        label_work=_fake_label_work("Seed"),
        name_initial=True,
    )
    assert shell.dirty == set()
    for j in shell.topic_ids():
        assert shell.labels[j].startswith("Seed")
        assert not is_placeholder_label(shell.labels[j], j)


def test_split_auto_names_children_and_parent_lineage():
    """Propose split → parent + children LLM-named; lineage kept."""
    X, fit, phrases = _planted(seed=9)
    shell = SubjectGrainShell(
        X, fit, phrases, seed=9, label_work=_fake_label_work("Parent")
    )
    assert is_placeholder_label(shell.labels[0], 0)
    shell.split(0)
    parent_name = shell.pending_proposal["parent_label"]
    assert parent_name.startswith("Parent")
    assert shell.pending_proposal["named"] is True
    for c in shell.proposed_topic_ids():
        assert shell.parent_of[c] == parent_name
        assert shell.labels[c].startswith("Parent")
        assert not is_placeholder_label(shell.labels[c], c)
        assert "(unnamed)" not in shell.labels[c]


def test_split_name_children_false_leaves_unnamed():
    X, fit, phrases = _planted(seed=11)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "Alpha", 1: "Beta", 2: "Gamma"},
        seed=11,
        label_work=_fake_label_work("Child"),
    )
    shell.split(1, name_children=False)
    for c in shell.proposed_topic_ids():
        assert "(unnamed)" in shell.labels[c]
    shell.name_proposal()
    for c in shell.proposed_topic_ids():
        assert shell.labels[c].startswith("Child")


def test_proposed_split_lineage_name_accept(tmp_path: Path):
    X, fit, phrases = _planted(seed=7)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "Alpha", 1: "Beta", 2: "Gamma"},
        seed=7,
        label_work=_fake_label_work("Child"),
    )
    shell.split(1)
    assert shell.pending_proposal is not None
    assert shell.pending_proposal["parent_label"] == "Beta"
    assert shell.pending_proposal["named"] is True
    children = shell.proposed_topic_ids()
    assert len(children) == 2
    for c in children:
        assert shell.parent_of[c] == "Beta"
        assert shell.labels[c].startswith("Child")
        assert "(unnamed)" not in shell.labels[c]

    cat = shell.catalogue()
    for c in children:
        row = cat.loc[cat["topic"] == c].iloc[0]
        assert row["parent_label"] == "Beta"
        assert bool(row["proposed"]) is True

    # Geometry: proposed view in parent U_q
    pytest.importorskip("matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    fig_path = tmp_path / "proposed_split.png"
    shell.fit_view(focus=children[0], path=str(fig_path), show=False)
    assert fig_path.exists()

    with pytest.raises(ValueError, match="pending"):
        shell.lock()

    assert shell.accept_proposal() is True
    assert shell.pending_proposal is None
    cat2 = shell.catalogue()
    for c in children:
        row = cat2.loc[cat2["topic"] == c].iloc[0]
        assert row["parent_label"] == "Beta"
        assert bool(row["proposed"]) is False

    artefact = shell.lock(path=tmp_path / "lock.json")
    assert "parent_of" in artefact
    assert any(v == "Beta" for v in artefact["parent_of"].values())


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
    shell.merge([0, 1], name_merged=False)
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
    shell.merge([0, 1], name_merged=False)
    with pytest.raises(ValueError, match="label_work"):
        shell.name_dirty()


def test_name_after_action_toggle():
    X, fit, phrases = _planted(seed=5)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "A", 1: "B", 2: "C"},
        seed=5,
        label_work=_fake_label_work("Auto"),
        name_after_action=True,
    )
    shell.merge([0, 1])
    assert shell.pending_proposal is not None
    assert shell.dirty == set()
    assert any(v.startswith("Auto") for v in shell.labels.values())
    shell.accept_proposal()


def test_rebuild_label_work_from_client():
    from multilogue.dummy import FakeClient

    X, fit, phrases = _planted(seed=7)
    client = FakeClient()
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        seed=7,
        label_client=client,
        label_prompt=(
            "Custom title only. Return JSON with label and description.\n"
            "Phrases:\n<<PHRASES>>"
        ),
        label_model="fake-small",
        name_initial=False,
    )
    assert shell.label_work is not None
    assert "<<PHRASES>>" in shell.label_prompt
    shell.rebuild_label_work(
        prompt=(
            "Even shorter. JSON keys label, description.\n<<PHRASES>>"
        ),
        model="fake-small",
    )
    assert "Even shorter" in shell.label_prompt
    assert "Even shorter" in shell.label_work.config["prompt_template"]
    named = shell.name_catalogue()
    assert named
    assert all(not is_placeholder_label(shell.labels[j], j) for j in named)


def test_name_catalogue_force_renames_existing():
    from multilogue.cluster import make_label_work
    from multilogue.dummy import FakeClient

    X, fit, phrases = _planted(seed=8)
    client = FakeClient()
    work = make_label_work(
        client,
        system="sys",
        prompt_template="Label these:\n<<PHRASES>>",
        model="fake-small",
    )
    shell = SubjectGrainShell(
        X, fit, phrases, seed=8, label_work=work, name_initial=True
    )
    before = dict(shell.labels)
    assert shell.dirty == set()
    # Without force, already-named topics are skipped
    assert shell.name_catalogue() == []
    assert shell.labels == before
    # Prompt change must stick on the live work.config used by split/name
    shell.rebuild_label_work(
        prompt="Re-label with new prompt:\n<<PHRASES>>",
        model="fake-small",
    )
    assert "Re-label" in work.config["prompt_template"]
    renamed = shell.name_catalogue(force=True)
    assert set(renamed) == set(shell.topic_ids())
    # FakeClient still derives from exemplars; ensure we actually called again
    assert client.calls.count("cluster_label") >= 2 * shell.k


def test_widgets_include_prompt_and_model():
    from multilogue.dummy import FakeClient

    X, fit, phrases = _planted(seed=6)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        seed=6,
        label_client=FakeClient(),
        label_model="fake-small",
    )
    if not ipywidgets_available():
        with pytest.raises(ImportError, match="ipywidgets"):
            shell.widgets()
        return
    ui = shell.widgets()
    assert ui is not None
    # Walk children for Textarea / Dropdown with labelling controls
    from ipywidgets import Dropdown, Textarea

    found_ta = found_dd = False

    def _walk(w):
        nonlocal found_ta, found_dd
        if isinstance(w, Textarea) and "PHRASES" in (w.value or ""):
            found_ta = True
        if isinstance(w, Dropdown) and "fake-small" in list(w.options):
            found_dd = True
        children = getattr(w, "children", None) or ()
        for c in children:
            _walk(c)

    _walk(ui)
    assert found_ta and found_dd


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


def test_shell_k1_entry_split_grows_grain():
    X, fit, phrases = _planted(k=2, seed=20)
    grain = initial_assess_fit(X, k=1, sigma2_mode="fixed", sigma2=0.12, seed=20)
    shell = SubjectGrainShell(
        X, grain, phrases, seed=20, sigma2_mode="fixed", em_max_iter_accept=15
    )
    assert shell.k == 1
    shell.split(0, name_children=False)
    assert shell.k == 2
    assert shell.pending_proposal is not None
    assert shell.accept_proposal()
    assert shell.pending_proposal is None
    assert shell.k == 2


def test_shell_fixed_sigma2_holds_across_merge():
    X, fit, phrases = _planted(seed=21)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "A", 1: "B", 2: "C"},
        seed=21,
        sigma2_mode="fixed",
        em_max_iter_accept=20,
    )
    shell.set_sigma2(0.17)
    assert shell.fit["sigma2"] == pytest.approx(0.17)
    shell.merge([0, 1], name_merged=False)
    assert shell.fit["sigma2"] == pytest.approx(0.17)
    shell.accept_proposal()
    assert shell.fit["sigma2"] == pytest.approx(0.17)
    assert shell.sigma2_mode == "fixed"


def test_shell_profile_accept_updates_sigma2_and_lock_extra(tmp_path: Path):
    X, fit, phrases = _planted(seed=22)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        labels={0: "A", 1: "B", 2: "C"},
        seed=22,
        sigma2_mode="profile",
        em_max_iter_accept=12,
        em_max_iter_preview=1,
    )
    before = float(shell.fit["sigma2"])
    shell.merge([0, 1], name_merged=False)
    R_pending = shell.responsibilities.copy()
    # Propose keeps parent σ²; Accept re-profiles geometry but holds R
    assert shell.fit["sigma2"] == pytest.approx(before)
    shell.accept_proposal()
    assert float(shell.fit["sigma2"]) > 0
    np.testing.assert_allclose(shell.responsibilities, R_pending, atol=1e-12)
    lock = shell.lock(path=tmp_path / "lock.json")
    assert lock["sigma2_mode"] == "profile"
    assert lock["em_max_iter_accept"] == 12
    assert lock["em_max_iter_preview"] == 1


def test_merge_preview_uses_preview_iter_budget():
    X, fit, phrases = _planted(seed=23)
    shell = SubjectGrainShell(
        X,
        fit,
        phrases,
        seed=23,
        em_max_iter_preview=1,
        em_max_iter_accept=25,
    )
    payload = shell.merge_preview_payload([0, 1])
    assert payload is not None
    assert payload["merged_id"] is not None
    # Preview must not mutate shell state
    assert shell.k == 3
    assert shell.pending_proposal is None
