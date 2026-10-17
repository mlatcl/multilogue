"""Soft document topic histograms (CIP-0017)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from multilogue import distance as dd


class TestSoftDocumentHistograms:
    def test_rows_sum_to_one_and_small_docs_dropped(self):
        # doc a: 60 phrases with mass 1 each → mass 60; doc b: 10 → dropped
        doc_ids = ["a"] * 60 + ["b"] * 10
        R = np.zeros((70, 3))
        R[:30, 0] = 1.0
        R[30:60, 1] = 1.0
        R[60:, 2] = 1.0
        P, docs, mass = dd.document_soft_topic_distributions(
            doc_ids, R, min_mass=50.0
        )
        assert docs == ["a"]
        assert np.allclose(P.sum(axis=1), 1.0)
        assert np.allclose(P[0], [0.5, 0.5, 0.0])
        assert float(mass["a"]) == pytest.approx(60.0)

    def test_soft_mass_matches_sum_of_responsibilities(self):
        doc_ids = ["x", "x", "y", "y"]
        R = np.array(
            [
                [0.7, 0.3],
                [0.4, 0.6],
                [0.1, 0.9],
                [0.2, 0.8],
            ]
        )
        P, docs, mass = dd.document_soft_topic_distributions(
            doc_ids, R, min_mass=0.0
        )
        assert docs == ["x", "y"]
        # x: [1.1, 0.9] / 2.0
        np.testing.assert_allclose(P[docs.index("x")], [0.55, 0.45])
        np.testing.assert_allclose(P[docs.index("y")], [0.15, 0.85])
        assert float(mass["x"]) == pytest.approx(2.0)

    def test_hard_path_still_available(self):
        df = pd.DataFrame(
            {
                "doc_id": ["a"] * 60 + ["b"] * 10,
                "cluster": [0] * 30 + [1] * 30 + [2] * 10,
            }
        )
        P, docs, n = dd.document_cluster_distributions(df, 3, min_phrases=50)
        assert docs == ["a"]
        assert np.allclose(P[0], [0.5, 0.5, 0.0])

    def test_length_mismatch(self):
        with pytest.raises(ValueError, match="doc_ids length"):
            dd.document_soft_topic_distributions(["a"], np.eye(3), min_mass=0.0)
