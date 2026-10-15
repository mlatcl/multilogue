"""Small text utilities shared across stages (no model calls)."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from typing import Any


def sha(s: Any) -> str:
    return hashlib.sha256(str(s).encode("utf-8")).hexdigest()


def norm_ws(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def qnorm(s: Any) -> str:
    """Normalise for quote matching: lower case, letters/digits/apostrophes only."""
    return re.sub(
        r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", str(s).lower().replace("’", "'"))
    ).strip()


def quote_support(quote: Any, source: Any) -> float:
    """1.0 = verbatim. Otherwise the share of the quote's words found, in order, in the source.

    Quotes joined with ' … ' are checked part by part.
    """
    parts = [p for p in re.split(r"\s*(?:…|\.\.\.)\s*", str(quote or "")) if qnorm(p)]
    if not parts:
        return 0.0
    src = qnorm(source)
    src_t = src.split()
    total = matched = 0
    for part in parts:
        q = qnorm(part)
        qt = q.split()
        total += len(qt)
        if f" {q} " in f" {src} ":
            matched += len(qt)
        else:
            matched += sum(
                b.size
                for b in difflib.SequenceMatcher(
                    None, qt, src_t, autojunk=False
                ).get_matching_blocks()
            )
    return round(matched / total, 3) if total else 0.0


def parse_json(text: str | None) -> Any:
    x = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return json.loads(x)
    except Exception:
        a, b = x.find("{"), x.rfind("}")
        if a >= 0 and b > a:
            return json.loads(x[a : b + 1])
        raise ValueError("Reply was not valid JSON") from None


def get_list(d: Any, key: str) -> list:
    """The list under ``key``, or the first list in the reply if the model used another name."""
    if isinstance(d, dict):
        if isinstance(d.get(key), list):
            return d[key]
        for v in d.values():
            if isinstance(v, list):
                return v
    return d if isinstance(d, list) else []
