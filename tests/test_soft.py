"""Tests for multilogue.soft (PPCA mixtures + σ²-by-EMD)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from multilogue import soft as ms

ot = pytest.importorskip("ot", reason="POT not installed (pip install pot)")


def _centroids(k=24, dim=10, seed=0):
    rng = np.random.default_rng(seed)
    C = rng.normal(size=(k, dim))
    return C / np.linalg.norm(C, axis=1, keepdims=True)


def _mappings(k=24, n_lenses=6, n_runs=3, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_runs):
        perm = rng.permutation(k)
        out.append(
            {
                f"L{j}": {"cluster_ids": perm[j::n_lenses].tolist()}
                for j in range(n_lenses)
            }
        )
    return out


class TestMixtureWeights:
    def test_rows_sum_to_one(self):
        C = _centroids()
        mapping = _mappings(n_runs=1)[0]
        W, names = ms.compute_mixture_weights(C, mapping, sigma2=0.05)
        assert W.shape == (24, len(names))
        assert np.allclose(W.sum(axis=1), 1.0)

    def test_soft_mapping_from_hard(self):
        hard = {0: "A", 1: "A", 2: "B"}
        soft = ms.soft_mapping_from_hard(hard)
        assert soft["A"]["cluster_ids"] == [0, 1]
        assert soft["B"]["cluster_ids"] == [2]


class TestSigma2Selection:
    def test_constrained_avoids_degenerate_end(self):
        grid = np.logspace(-4, 2, 25)
        # Shape like real curves: EMD falls as memberships become uniform.
        eff = np.concatenate(
            [
                np.linspace(1.0, 1.3, 10),
                [2.09, 4.52, 7.54],
                np.linspace(9.25, 10.2, 12),
            ]
        )
        emd = np.concatenate(
            [
                np.full(10, 0.064),
                [0.0596, 0.0572, 0.0555],
                np.linspace(0.0554, 0.0549, 12),
            ]
        )
        curve = pd.DataFrame(
            {"sigma2": grid, "mean_eff_support": eff, "mean_emd": emd}
        )
        s2 = ms.select_sigma2_constrained(curve, n_lenses=10.2)
        assert s2 == pytest.approx(grid[11])

    def test_band_fallback(self):
        c = pd.DataFrame(
            {
                "sigma2": [0.1, 1.0],
                "mean_eff_support": [2.04, 9.0],
                "mean_emd": [0.2, 0.1],
            }
        )
        assert ms.select_sigma2_constrained(c, 10.2) == pytest.approx(1.0)

    @pytest.mark.parametrize("seed", [0, 1])
    def test_sweep_matches_band_rule(self, seed):
        C = _centroids(seed=seed)
        mappings = _mappings(seed=seed + 10)
        res = ms.sigma2_sweep_select(C, mappings)
        curve = pd.DataFrame(res["curve"])
        assert ms.select_sigma2_constrained(curve, ms.mean_n_lenses(mappings)) == (
            pytest.approx(res["sigma2_best"])
        )
        assert res["selection"] in (
            "constrained",
            "unconstrained (no σ² in meaningful-soft zone)",
        )
        assert len(res["mixture_weights"]) == len(mappings)
