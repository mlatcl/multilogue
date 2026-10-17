import pandas as pd

from multilogue.report import cluster_catalogue, findings_markdown, write_findings


def test_findings_markdown_and_catalogue(tmp_path):
    phrases = pd.DataFrame(
        {
            "phrase_id": ["a", "b", "c", "d"],
            "doc_id": ["d1", "d1", "d2", "d2"],
            "phrase": ["worry one", "worry two", "good path", "worry three"],
            "kind": ["concern", "concern", "benefit", "concern"],
            "format": ["dialogue", "survey", "dialogue", "survey"],
            "cluster": [0, 0, 1, 1],
            "cluster_label": ["Safety", "Safety", "Access", "Access"],
            "lens": ["L1", "L1", "L2", "L2"],
            "centroid_sim": [0.9, 0.8, 0.7, 0.6],
        }
    )
    compare = pd.DataFrame(
        {
            "lens": ["L1", "L2"],
            "dialogue_pct": [40.0, 60.0],
            "survey_pct": [70.0, 30.0],
            "difference": [30.0, -30.0],
            "clear": [True, True],
        }
    )
    cat = cluster_catalogue(phrases)
    assert len(cat) == 2
    assert "worry one" in cat.loc[0, "examples"]
    md = findings_markdown(phrases, compare=compare, title="Test findings")
    assert "### 0. Safety" in md
    assert "## Concerns (by format)" in md
    assert "Format contrast" in md
    path = write_findings(phrases, tmp_path / "findings.md", compare=compare)
    assert path.is_file()
    assert (tmp_path / "cluster_catalogue.csv").is_file()
