from pathlib import Path

import pandas as pd

from multilogue.assess_base import empty_unit_flags, unit_size_table
from multilogue.report import evidence_pack
from multilogue.validate import stratified_sample


def test_stratified_sample():
    df = pd.DataFrame({"g": ["a"] * 5 + ["b"] * 5, "x": range(10)})
    s = stratified_sample(df, by="g", n_per_stratum=2, random_state=0)
    assert len(s) == 4
    assert set(s.g) == {"a", "b"}


def test_evidence_pack(tmp_path: Path):
    df = pd.DataFrame(
        {
            "lens": ["L1", "L1"],
            "cluster": [0, 0],
            "cluster_label": ["privacy", "privacy"],
            "phrase": ["p1", "p2"],
            "quote": ["q1", "q2"],
            "format": ["A", "B"],
            "kind": ["concern", "concern"],
        }
    )
    path = evidence_pack(df, tmp_path / "pack.html")
    html = path.read_text()
    assert "privacy" in html and "Evidence pack" in html


def test_assess_base():
    units = [
        {"unit_id": "u1", "doc_id": "d1", "text": "one two three four five"},
        {"unit_id": "u2", "doc_id": "d1", "text": "hi"},
    ]
    sizes = unit_size_table(units)
    assert len(sizes) == 2
    assert empty_unit_flags(units, min_words=4) == ["u2"]
