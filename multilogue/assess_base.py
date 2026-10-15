"""Question-agnostic assess helpers (no LLM, no research-question filters)."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

import pandas as pd


def unit_size_table(units: Sequence[dict], *, text_key: str = "text") -> pd.DataFrame:
    """Word counts and character lengths for each unit."""
    rows = []
    for u in units:
        text = str(u.get(text_key) or "")
        rows.append(
            {
                "unit_id": u.get("unit_id"),
                "doc_id": u.get("doc_id"),
                "n_chars": len(text),
                "n_words": len(text.split()),
            }
        )
    return pd.DataFrame(rows)


def docs_per_group(units: Sequence[dict], group_key: str) -> pd.DataFrame:
    """Document counts by a metadata group present on units."""
    rows = [(u.get("doc_id"), u.get(group_key)) for u in units]
    df = pd.DataFrame(rows, columns=["doc_id", "group"]).dropna()
    return (
        df.drop_duplicates()
        .groupby("group")
        .size()
        .reset_index(name="n_docs")
        .sort_values("n_docs", ascending=False)
    )


def empty_unit_flags(units: Sequence[dict], *, text_key: str = "text", min_words: int = 4) -> list[str]:
    """Return unit_ids that are empty or below ``min_words``."""
    bad = []
    for u in units:
        n = len(str(u.get(text_key) or "").split())
        if n < min_words:
            bad.append(str(u.get("unit_id")))
    return bad


def token_frequency(texts: Iterable[str], *, top_n: int = 50) -> pd.DataFrame:
    """Simple unigram counts for assess-time vocabulary inspection."""
    c: Counter = Counter()
    for t in texts:
        c.update(w for w in str(t).lower().split() if w.isalpha())
    return pd.DataFrame(c.most_common(top_n), columns=["token", "count"])
