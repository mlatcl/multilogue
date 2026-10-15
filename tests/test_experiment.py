from pathlib import Path

from multilogue.dummy import FakeClient, make_units
from multilogue.experiment import run_validation_experiment


def test_make_units_synthetic_only():
    units = make_units(n_docs_per_group=2, units_per_doc=2)
    assert len(units) == 8
    assert all(u["meta"]["synthetic"] for u in units)
    assert {u["group"] for u in units} == {"group_a", "group_b"}


def test_fake_client_no_network():
    c = FakeClient()
    text = "I am worried the computer will make mistakes about benefits. extra"
    reply = c.complete("ext_concern", "s", text, "m")
    assert "||" in reply
    vecs = c.embed(["hello world", "data privacy"], "fake-embed")
    assert len(vecs) == 2 and len(vecs[0]) == 32


def test_validation_experiment_tmp(tmp_path: Path):
    summary = run_validation_experiment(
        tmp_path / "run",
        n_docs_per_group=3,
        units_per_doc=2,
        k=3,
        quiet=True,
    )
    assert summary["synthetic"] is True
    assert summary["n_units"] == 12
    assert summary["n_phrases"] >= 4
    assert (tmp_path / "run" / "tables" / "phrases_clustered.csv").exists()
    assert (tmp_path / "run" / "tables" / "multiverse.csv").exists()
    assert (tmp_path / "run" / "evidence_pack.html").exists()
    # Ensure we never wrote under a path named like real data corpora
    assert "pdf" not in summary
    assert "transcript" not in str(summary).lower()
