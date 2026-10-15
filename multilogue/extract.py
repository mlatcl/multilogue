"""Generic phrase extraction: kind + template + sentinel + optional quote gate."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Callable

import pandas as pd

from .text import quote_support


def parse_items(text: str | None, sentinel: str) -> list[tuple[str, str]]:
    """Parse ``phrase || quote`` lines; skip sentinel replies."""
    items = []
    for line in (text or "").splitlines():
        l = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", line).strip()
        if not l or re.fullmatch(
            r"\W*" + re.escape(sentinel) + r"\W*", l.upper().replace(" ", "_")
        ):
            continue
        phrase, quote = (l.split("||", 1) + [""])[:2] if "||" in l else (l, "")
        phrase = phrase.strip().strip('"“”').rstrip(" .").strip()
        quote = quote.strip().strip('"“”').strip()
        if phrase:
            items.append((phrase, quote))
    return items


def make_extract_work(
    client,
    *,
    kind: str,
    system: str,
    user_for_unit: Callable[[dict], str],
    model: str,
    sentinel: str,
    quote_threshold: float | None = 0.8,
    source_text: Callable[[dict], str] | None = None,
    stage_tag: str = "ext",
    max_items: int = 8,
    min_words: int = 2,
    max_words: int = 15,
) -> Callable[[dict], dict]:
    """Build a ``work_fn`` for :class:`StageRunner` that extracts one kind of phrase."""

    def _source(u: dict) -> str:
        if source_text is not None:
            return source_text(u)
        return str(u.get("extract_text") or u.get("text") or "")

    def work(u: dict) -> dict:
        reply = client.complete(f"{stage_tag}_{kind}", system, user_for_unit(u), model=model)
        stats: Counter = Counter()
        out: list[dict[str, Any]] = []
        items = parse_items(reply, sentinel)
        if not items:
            stats["none_returned"] += 1
        seen: set[str] = set()
        src = _source(u)
        for phrase, quote in items[:max_items]:
            stats["returned"] += 1
            n = len(phrase.split())
            if n < min_words or n > max_words:
                stats["dropped_bad_length"] += 1
                continue
            if phrase.lower() in seen:
                stats["dropped_duplicate"] += 1
                continue
            seen.add(phrase.lower())
            sup = quote_support(quote, src) if quote else 0.0
            if quote_threshold is None:
                verified = True
            else:
                verified = bool(quote) and sup >= quote_threshold
                if quote and not verified:
                    stats["kept_unverified"] += 1
            stats["kept"] += 1
            out.append(
                {
                    "phrase": phrase,
                    "quote": quote,
                    "quote_support": sup,
                    "verified": verified,
                }
            )
        return {"items": out, "stats": dict(stats)}

    return work


def phrase_table(
    extraction: dict[str, dict[str, dict]],
    units_by_id: dict[str, dict],
    *,
    kinds: list[str] | None = None,
    extra_unit_fields: list[str] | None = None,
) -> pd.DataFrame:
    """Flatten ``{kind: {unit_id: result}}`` into a phrase DataFrame."""
    kinds = kinds or list(extraction)
    extra = extra_unit_fields or []
    rows = []
    for kind in kinds:
        for uid, res in extraction.get(kind, {}).items():
            u = units_by_id[uid]
            for i, it in enumerate(res.get("items", []), 1):
                row = {
                    "phrase_id": f"{kind}|{uid}|{i}",
                    "kind": kind,
                    "unit_id": uid,
                    "doc_id": u.get("doc_id"),
                    **it,
                }
                for f in extra:
                    row[f] = u.get(f)
                rows.append(row)
    return pd.DataFrame(rows)


def yield_report(
    extraction: dict[str, dict[str, dict]],
    unit_ids_by_group: dict[str, list[str]],
    *,
    kinds: list[str] | None = None,
    missing_by_kind: dict[str, set[str]] | None = None,
) -> pd.DataFrame:
    """Per kind × group yield diagnostics."""
    kinds = kinds or list(extraction)
    missing_by_kind = missing_by_kind or {}
    rows = []
    for kind in kinds:
        for group, ids in unit_ids_by_group.items():
            st: Counter = Counter()
            for uid in ids:
                if uid in extraction.get(kind, {}):
                    st.update(extraction[kind][uid].get("stats", {}))
            done = sum(uid in extraction.get(kind, {}) for uid in ids)
            kept = st["kept"]
            unverified = st["kept_unverified"]
            rows.append(
                {
                    "kind": kind,
                    "group": group,
                    "units": len(ids),
                    "units_done": done,
                    "pct_units_none": round(100 * st["none_returned"] / max(1, done), 1),
                    "phrases_returned": st["returned"],
                    "kept": kept,
                    "pct_kept_verified": round(100 * (kept - unverified) / max(1, kept), 1),
                    "dropped_bad_length": st["dropped_bad_length"],
                    "dropped_duplicate": st["dropped_duplicate"],
                    "failed_units": sum(uid in missing_by_kind.get(kind, ()) for uid in ids),
                }
            )
    return pd.DataFrame(rows)


def vocabulary_audit(
    phrases: pd.DataFrame,
    group_col: str,
    meta_words: list[str] | None = None,
    phrase_col: str = "phrase",
) -> pd.DataFrame:
    """Most frequent words/bigrams per group; flags process words the prompt may have planted."""
    stop = set(
        "a an the of to and or in for on with by is are be from as at that this it their its".split()
    )
    meta_words = meta_words or []
    rows = []
    for group, g in phrases.groupby(group_col):
        c: Counter = Counter()
        for t in g[phrase_col]:
            w = re.findall(r"[a-z']+", str(t).lower())
            c.update(w)
            c.update(" ".join(p) for p in zip(w, w[1:]))
        top = [
            (k, v)
            for k, v in c.most_common(400)
            if k not in stop and not all(x in stop for x in k.split())
        ][:25]
        rows += [
            {
                group_col: group,
                "term": k,
                "count": v,
                "meta_word": any(m in k for m in meta_words),
            }
            for k, v in top
        ]
    return pd.DataFrame(rows)
