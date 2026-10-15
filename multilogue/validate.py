"""Validation scaffolding: sampling for blind sheets and agreement helpers.

Study-specific coding schemes (grounds, experience word lists) stay in consumers.
"""
from __future__ import annotations

import pandas as pd

from .weight import kappa, rank_agreement

__all__ = ["kappa", "rank_agreement", "stratified_sample"]


def stratified_sample(
    df: pd.DataFrame,
    *,
    by: str | list[str],
    n_per_stratum: int,
    random_state: int = 0,
) -> pd.DataFrame:
    """Sample up to ``n_per_stratum`` rows from each stratum of ``by``."""
    keys = [by] if isinstance(by, str) else list(by)
    parts = []
    for _, g in df.groupby(keys, dropna=False):
        parts.append(g.sample(n=min(n_per_stratum, len(g)), random_state=random_state))
    if not parts:
        return df.iloc[0:0].copy()
    return pd.concat(parts).reset_index(drop=True)
