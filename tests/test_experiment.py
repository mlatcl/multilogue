from pathlib import Path

from multilogue.dummy import FakeClient, make_units
from multilogue.experiment import (
    format_tagged_units,
    gold_argument_format_compare,
    run_formats_complexity_demo,
    run_validation_experiment,
)


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


def test_format_tagged_units():
    units = format_tagged_units(n_docs_per_group=2, units_per_doc=1)
    assert {u["format"] for u in units} == {"workshop", "survey"}
    assert all(u["format"] == u["group"] for u in units)


def test_gold_argument_format_compare():
    units = [
        {"unit_id": "d1", "doc_id": "D1", "format": "dialogue", "text": "x",
         "meta": {"code": "premise"}},
        {"unit_id": "d2", "doc_id": "D1", "format": "dialogue", "text": "x",
         "meta": {"code": "premise"}},
        {"unit_id": "d3", "doc_id": "D2", "format": "dialogue", "text": "x",
         "meta": {"code": "mpos"}},
        {"unit_id": "s1", "doc_id": "S1", "format": "survey", "text": "x",
         "meta": {"code": "mpos"}},
        {"unit_id": "s2", "doc_id": "S1", "format": "survey", "text": "x",
         "meta": {"code": "mpos"}},
        {"unit_id": "s3", "doc_id": "S2", "format": "survey", "text": "x",
         "meta": {"code": "premise"}},
    ]
    tab = gold_argument_format_compare(units, formats=("dialogue", "survey"))
    assert list(tab["metric"]) == ["mpos_share", "premise_share"]
    # dialogue docs: D1=0% mpos, D2=100% → 50%; survey: S1=100%, S2=0% → 50%
    mpos = tab.set_index("metric").loc["mpos_share"]
    assert abs(mpos["dialogue_pct"] - 50.0) < 1e-6
    assert abs(mpos["survey_pct"] - 50.0) < 1e-6


def test_formats_complexity_demo_tmp(tmp_path: Path):
    summary = run_formats_complexity_demo(
        tmp_path / "fmt",
        n_docs_per_group=3,
        units_per_doc=2,
        k=4,
        lens_runs=2,
        quiet=True,
    )
    assert summary["synthetic"] is True
    assert summary["formats"] == ["workshop", "survey"]
    tables = tmp_path / "fmt" / "tables"
    assert (tables / "group_compare_format_lenses.csv").exists()
    assert (tables / "multiverse_format_gap.csv").exists()
    assert (tables / "variance_shares_format_gap.csv").exists()
    assert (tmp_path / "fmt" / "checkpoints").is_dir()
