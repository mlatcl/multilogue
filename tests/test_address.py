"""Tests for Address-stage cluster curation and soft re-compare."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from multilogue import address as addr

ot = pytest.importorskip("ot", reason="POT not installed")


def _toy_phrases(n_per=5, k=4, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    lenses = ["Parken und Abstellen", "Radwege und Führung", "Other", "Other"]
    labels = ["park", "path-bag", "misc-a", "misc-b"]
    for c in range(k):
        for i in range(n_per):
            phrase = (
                "Fahrradparkmöglichkeiten erweitern"
                if c == 0 and i < 2
                else f"phrase-{c}-{i}"
            )
            rows.append(
                {
                    "phrase_id": f"{c}-{i}",
                    "phrase": phrase,
                    "cluster": c,
                    "cluster_label": labels[c],
                    "lens": lenses[c],
                    "format": "dialogue" if i % 2 == 0 else "survey",
                    "doc_id": f"d{c}-{i % 2}",
                    "kind": "concern",
                }
            )
    ph = pd.DataFrame(rows)
    # make cluster 1 large
    extra = []
    for i in range(20):
        extra.append(
            {
                "phrase_id": f"big-{i}",
                "phrase": f"Radweg-problem-{i}",
                "cluster": 1,
                "cluster_label": "path-bag",
                "lens": "Radwege und Führung",
                "format": "dialogue" if i % 2 == 0 else "survey",
                "doc_id": f"dbig-{i % 3}",
                "kind": "concern",
            }
        )
    ph = pd.concat([ph, pd.DataFrame(extra)], ignore_index=True)
    # singleton cluster 3
    ph = ph[ph.cluster != 3].copy()
    ph = pd.concat(
        [
            ph,
            pd.DataFrame(
                [
                    {
                        "phrase_id": "sing-0",
                        "phrase": "outlier singleton",
                        "cluster": 3,
                        "cluster_label": "misc-b",
                        "lens": "Other",
                        "format": "survey",
                        "doc_id": "dsing",
                        "kind": "concern",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    dim = 8
    E = rng.normal(size=(len(ph), dim))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    return ph, E


class TestCurationPrimitives:
    def test_move_phrases_by_keyword(self):
        ph, _ = _toy_phrases()
        out, n = addr.move_phrases_by_keyword(
            ph,
            from_cluster=0,
            to_cluster=2,
            pattern=r"park",
            to_label="park-label",
            to_lens="Parken und Abstellen",
        )
        assert n >= 1
        assert (out.loc[out.phrase.str.contains("park", case=False), "cluster"] == 2).all()

    def test_tighten_and_recompare(self, tmp_path):
        ph, E = _toy_phrases()
        # Map parking_from=0, parking_to needs a park lens cluster — use 2 as "parking"
        ph = ph.copy()
        ph.loc[ph.cluster == 2, "lens"] = "Parken und Abstellen"
        ph.loc[ph.cluster == 2, "cluster_label"] = "Fahrradstellplätze verbessern"
        tight = addr.tighten_cimt_parking_path(
            ph,
            E,
            parking_from=0,
            parking_to=2,
            path_lens="Radwege und Führung",
        )
        assert tight["notes"]["parking_moved"] >= 1
        assert tight["notes"]["split"]["split"] is True
        curated = tight["phrases"]
        assert curated.cluster.nunique() >= 3
        contrasts = addr.recompute_format_contrasts(
            curated, E, sigma2=0.1, reps=20, n_perm=19, include_distance=False
        )
        assert contrasts["W"].shape[0] == int(curated.cluster.max()) + 1
        assert np.allclose(contrasts["W"].sum(axis=1), 1.0, atol=1e-5)
        out = addr.write_curated_tables(tmp_path / "curated", curated, contrasts)
        assert (out / "edited_lenses.yaml").is_file()
        assert (out / "phrases_clustered.csv").is_file()
