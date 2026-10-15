"""Multiverse enumeration and variance shares (Bell et al. 2022 style).

Paper-specific headline metrics (ℓ) are supplied by consumers via callbacks.
"""
from __future__ import annotations

import itertools
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd


def enumerate_configurations(dimensions: dict[str, list]) -> list[dict[str, Any]]:
    """Cartesian product of a dimensions dict → list of config dicts."""
    if not dimensions:
        return [{}]
    keys = list(dimensions.keys())
    value_lists = [dimensions[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in itertools.product(*value_lists)]


def run_multiverse(
    configs: Iterable[dict[str, Any]],
    evaluate: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    progress: bool = False,
) -> pd.DataFrame:
    """Evaluate every configuration via ``evaluate`` and return a results frame.

    ``evaluate(config)`` should return a dict of outcome metrics (and may echo
    dimension values). Dimension keys from ``config`` are merged into each row
    so variance decomposition can group by them.
    """
    configs = list(configs)
    if progress:
        try:
            from tqdm.auto import tqdm as _tqdm  # type: ignore
        except ImportError:

            def _tqdm(xs, **_):
                return xs
    else:

        def _tqdm(xs, **_):
            return xs

    rows: list[dict[str, Any]] = []
    for cfg in _tqdm(configs, desc="multiverse"):
        row = dict(cfg)
        row.update(evaluate(cfg))
        rows.append(row)
    return pd.DataFrame(rows)


def variance_decomposition(
    results_df: pd.DataFrame,
    metric: str,
    dimensions: list[str],
) -> pd.DataFrame:
    """One-way variance share per dimension — first-cut diagnostic.

    Shares do not sum to 1 in the presence of interactions.
    """
    y = results_df[metric].to_numpy(dtype=float)
    y = y[~np.isnan(y)]
    if y.size == 0:
        return pd.DataFrame({"dimension": dimensions, "variance_share": np.nan})
    grand_mean = float(y.mean())
    total_ss = float(((y - grand_mean) ** 2).sum())
    noise_floor = 1e-10 * (abs(grand_mean) + 1e-12)
    if total_ss <= noise_floor:
        return pd.DataFrame(
            {"dimension": dimensions, "variance_share": [0.0] * len(dimensions)}
        )

    shares = {}
    for dim in dimensions:
        if dim not in results_df.columns:
            shares[dim] = float("nan")
            continue
        between_ss = 0.0
        for _, group in results_df.groupby(dim):
            vals = group[metric].dropna().to_numpy(dtype=float)
            if vals.size == 0:
                continue
            between_ss += vals.size * (float(vals.mean()) - grand_mean) ** 2
        shares[dim] = between_ss / total_ss

    return (
        pd.DataFrame(
            {
                "dimension": dimensions,
                "variance_share": [shares[d] for d in dimensions],
            }
        )
        .sort_values("variance_share", ascending=False)
        .reset_index(drop=True)
    )
