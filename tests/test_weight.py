import numpy as np
import pandas as pd

from multilogue.weight import doc_binary_presence, doc_profile, group_compare, kappa


def test_doc_profile_and_group_compare():
    df = pd.DataFrame(
        {
            "doc_id": ["d1", "d1", "d2", "d2", "d3", "d3"],
            "group": ["A", "A", "A", "A", "B", "B"],
            "lens": ["x", "y", "x", "x", "y", "y"],
        }
    )
    P = doc_profile(df[df.group == "A"], "lens", ["x", "y"])
    assert list(P.columns) == ["x", "y"]
    rng = np.random.default_rng(0)
    out = group_compare(df, "group", "lens", ["x", "y"], rng, groups=["A", "B"], reps=200)
    assert "A_pct" in out.columns and "B_pct" in out.columns
    assert "difference" in out.columns


def test_doc_binary_presence():
    df = pd.DataFrame(
        {
            "doc_id": ["d1", "d1", "d2", "d3"],
            "year": [2020, 2020, 2020, 2021],
            "cluster": [0, 1, 0, 0],
        }
    )
    shares = doc_binary_presence(df, "cluster", "year")
    # 2020: 2 docs, cluster 0 in both → 1.0; cluster 1 in 1/2 → 0.5
    assert shares.loc[2020, 0] == 1.0
    assert shares.loc[2020, 1] == 0.5


def test_kappa():
    assert kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
