"""Evidence-pack HTML shell and small report helpers."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Sequence

import pandas as pd

from .llm import utcnow


def evidence_pack(
    phrases: pd.DataFrame,
    path: str | Path,
    *,
    lens_col: str = "lens",
    cluster_col: str = "cluster",
    label_col: str = "cluster_label",
    phrase_col: str = "phrase",
    quote_col: str = "quote",
    group_col: str | None = "format",
    kind_col: str | None = "kind",
    title: str = "Evidence pack",
    seed: int = 0,
    n_examples: int = 6,
) -> Path:
    """Write a simple HTML evidence pack. May contain participant quotes — do not commit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    esc = lambda s: html.escape(str(s))
    lenses = sorted(phrases[lens_col].dropna().unique()) if lens_col in phrases.columns else ["all"]
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>{esc(title)}</title>",
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:16px}",
        "h2{margin-top:2em;border-bottom:1px solid #ccc}.m{color:#666;font-size:13px}",
        ".cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}</style></head><body>",
        f"<h1>{esc(title)}</h1>",
        f"<p class='m'>{len(phrases)} points · generated {utcnow()[:16]} · "
        "may contain participant quotes</p>",
    ]
    for L in lenses:
        sub_l = phrases if lens_col not in phrases.columns else phrases[phrases[lens_col] == L]
        parts.append(f"<h2>{esc(L)}</h2>")
        clusters = sorted(sub_l[cluster_col].unique()) if cluster_col in sub_l.columns else [0]
        for c in clusters:
            sub = sub_l[sub_l[cluster_col] == c] if cluster_col in sub_l.columns else sub_l
            label = (
                sub[label_col].iloc[0]
                if label_col in sub.columns and len(sub)
                else f"cluster {c}"
            )
            parts.append(f"<h3>{esc(label)}</h3><p class='m'>{len(sub)} points</p>")
            if group_col and group_col in sub.columns:
                parts.append("<div class='cols'>")
                for g in sorted(sub[group_col].dropna().unique()):
                    s = sub[sub[group_col] == g]
                    s = s.sample(n=min(n_examples, len(s)), random_state=seed) if len(s) else s
                    items = _items_html(s, phrase_col, quote_col, kind_col, esc)
                    parts.append(f"<div><b>{esc(g)}</b><ul>{items}</ul></div>")
                parts.append("</div>")
            else:
                s = sub.sample(n=min(n_examples, len(sub)), random_state=seed) if len(sub) else sub
                parts.append(f"<ul>{_items_html(s, phrase_col, quote_col, kind_col, esc)}</ul>")
    parts.append("</body></html>")
    path.write_text("".join(parts), encoding="utf-8")
    return path


def _items_html(s: pd.DataFrame, phrase_col, quote_col, kind_col, esc) -> str:
    if not len(s):
        return "<li class='m'>none</li>"
    bits = []
    for r in s.itertuples():
        phrase = getattr(r, phrase_col, "")
        quote = getattr(r, quote_col, "") if quote_col in s.columns else ""
        kind = getattr(r, kind_col, "") if kind_col and kind_col in s.columns else ""
        kind_bit = f" <span class='m'>({esc(kind)})</span>" if kind != "" else ""
        quote_bit = f"<br><q>{esc(quote)}</q>" if quote != "" else ""
        bits.append(f"<li><b>{esc(phrase)}</b>{kind_bit}{quote_bit}</li>")
    return "".join(bits)


def write_manifest(path: str | Path, data: dict) -> Path:
    from .config import dump_json

    path = Path(path)
    dump_json(data, path)
    return path
