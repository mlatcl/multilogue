"""Question-agnostic assess helpers (no LLM, no research-question filters)."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable, Literal, Sequence

import pandas as pd

LangHint = Literal["de", "en", "auto"]

# Dialogue-ish defaults: flag units outside these word-count bands.
DEFAULT_UNIT_WORDS_MIN = 8
DEFAULT_UNIT_WORDS_MAX = 400

# Sentence length (words) extremes.
DEFAULT_SENT_WORDS_MIN = 3
DEFAULT_SENT_WORDS_MAX = 80

# Letter-token length extremes (OCR junk / fused tokens).
DEFAULT_WORD_LEN_MIN = 1
DEFAULT_WORD_LEN_MAX = 24

# Character-class share of "other" (non letter/digit/punct/space) above this → flag.
DEFAULT_OTHER_CHAR_SHARE = 0.05

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|(?<=\n)\s*")
_LETTER_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
_GERMAN_MARKS = set("äöüÄÖÜß")


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


def empty_unit_flags(
    units: Sequence[dict], *, text_key: str = "text", min_words: int = 4
) -> list[str]:
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


def unit_length_summary(
    sizes: pd.DataFrame,
    *,
    min_words: int = DEFAULT_UNIT_WORDS_MIN,
    max_words: int = DEFAULT_UNIT_WORDS_MAX,
) -> pd.DataFrame:
    """Percentile summary of unit word/char lengths plus band-flag counts."""
    if sizes is None or len(sizes) == 0:
        return pd.DataFrame()
    n = len(sizes)
    out = {
        "n_units": n,
        "n_words_p10": float(sizes["n_words"].quantile(0.10)),
        "n_words_p50": float(sizes["n_words"].quantile(0.50)),
        "n_words_p90": float(sizes["n_words"].quantile(0.90)),
        "n_chars_p50": float(sizes["n_chars"].quantile(0.50)),
        "n_below_min_words": int((sizes["n_words"] < min_words).sum()),
        "n_above_max_words": int((sizes["n_words"] > max_words).sum()),
        "min_words": min_words,
        "max_words": max_words,
    }
    return pd.DataFrame([out])


def flag_unit_length(
    units: Sequence[dict],
    *,
    text_key: str = "text",
    min_words: int = DEFAULT_UNIT_WORDS_MIN,
    max_words: int = DEFAULT_UNIT_WORDS_MAX,
) -> pd.DataFrame:
    """Per-unit length flags (too short / too long for dialogue-ish paragraphs)."""
    rows = []
    for u in units:
        text = str(u.get(text_key) or "")
        n = len(text.split())
        flag = None
        if n < min_words:
            flag = "too_short"
        elif n > max_words:
            flag = "too_long"
        if flag:
            rows.append(
                {
                    "unit_id": u.get("unit_id"),
                    "doc_id": u.get("doc_id"),
                    "n_words": n,
                    "flag": flag,
                }
            )
    return pd.DataFrame(rows)


def split_sentences(text: str) -> list[str]:
    """Heuristic sentence split on `.?!…` and newlines."""
    text = str(text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p and p.strip()]
    return parts or [text]


def sentence_length_table(
    units: Sequence[dict], *, text_key: str = "text"
) -> pd.DataFrame:
    """One row per sentence: unit_id, sentence index, word count."""
    rows = []
    for u in units:
        sents = split_sentences(str(u.get(text_key) or ""))
        for i, s in enumerate(sents):
            rows.append(
                {
                    "unit_id": u.get("unit_id"),
                    "doc_id": u.get("doc_id"),
                    "sent_ix": i,
                    "n_words": len(s.split()),
                    "n_chars": len(s),
                }
            )
    return pd.DataFrame(rows)


def flag_sentence_length(
    sent: pd.DataFrame,
    *,
    min_words: int = DEFAULT_SENT_WORDS_MIN,
    max_words: int = DEFAULT_SENT_WORDS_MAX,
) -> pd.DataFrame:
    """Sentences outside the word-count band."""
    if sent is None or len(sent) == 0:
        return pd.DataFrame()
    out = sent.copy()
    flag = pd.Series([None] * len(out), dtype=object)
    flag = flag.mask(out["n_words"] < min_words, "too_short")
    flag = flag.mask(out["n_words"] > max_words, "too_long")
    out["flag"] = flag
    return out.loc[out["flag"].notna()].reset_index(drop=True)


def infer_lang(text: str, *, hint: LangHint = "auto") -> str:
    """Return ``de`` or ``en``. Auto uses German diacritic rate."""
    if hint in ("de", "en"):
        return hint
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    german = sum(1 for c in letters if c in _GERMAN_MARKS)
    return "de" if german / len(letters) >= 0.01 else "en"


def letter_tokens(text: str) -> list[str]:
    """Unicode letter tokens (no digits)."""
    return _LETTER_TOKEN.findall(str(text or "").lower())


def word_length_table(
    units: Sequence[dict],
    *,
    text_key: str = "text",
    lang: LangHint = "auto",
) -> pd.DataFrame:
    """One row per letter-token with length and inferred language."""
    rows = []
    for u in units:
        text = str(u.get(text_key) or "")
        unit_lang = u.get("lang") or infer_lang(text, hint=lang)
        for tok in letter_tokens(text):
            rows.append(
                {
                    "unit_id": u.get("unit_id"),
                    "doc_id": u.get("doc_id"),
                    "lang": unit_lang,
                    "token": tok,
                    "n_chars": len(tok),
                }
            )
    return pd.DataFrame(rows)


def flag_word_length(
    words: pd.DataFrame,
    *,
    min_len: int = DEFAULT_WORD_LEN_MIN,
    max_len: int = DEFAULT_WORD_LEN_MAX,
) -> pd.DataFrame:
    """Tokens outside the length band (OCR fused strings, debris)."""
    if words is None or len(words) == 0:
        return pd.DataFrame()
    out = words.copy()
    flag = pd.Series([None] * len(out), dtype=object)
    flag = flag.mask(out["n_chars"] < min_len, "too_short")
    flag = flag.mask(out["n_chars"] > max_len, "too_long")
    out["flag"] = flag
    return out.loc[out["flag"].notna()].reset_index(drop=True)


def _char_class(ch: str) -> str:
    if ch.isalpha():
        return "letter"
    if ch.isdigit():
        return "digit"
    if ch.isspace():
        return "space"
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "punct"
    if cat.startswith("C") or ch == "\ufffd":
        return "other"
    return "other"


def character_inventory(
    units: Sequence[dict], *, text_key: str = "text"
) -> pd.DataFrame:
    """Aggregate character-class counts across units."""
    counts: Counter = Counter()
    n_chars = 0
    for u in units:
        for ch in str(u.get(text_key) or ""):
            counts[_char_class(ch)] += 1
            n_chars += 1
    rows = []
    for cls in ("letter", "digit", "punct", "space", "other"):
        n = int(counts.get(cls, 0))
        rows.append(
            {
                "char_class": cls,
                "n": n,
                "share": (n / n_chars) if n_chars else 0.0,
            }
        )
    return pd.DataFrame(rows)


def unusual_codepoints(
    units: Sequence[dict],
    *,
    text_key: str = "text",
    top_n: int = 20,
) -> pd.DataFrame:
    """Most frequent codepoints classified as ``other`` (controls, replacement, etc.)."""
    c: Counter = Counter()
    for u in units:
        for ch in str(u.get(text_key) or ""):
            if _char_class(ch) == "other":
                c[ch] += 1
    rows = []
    for ch, n in c.most_common(top_n):
        rows.append(
            {
                "char": ch,
                "codepoint": f"U+{ord(ch):04X}",
                "name": unicodedata.name(ch, "UNKNOWN"),
                "category": unicodedata.category(ch),
                "n": n,
            }
        )
    return pd.DataFrame(rows)


def flag_unusual_characters(
    units: Sequence[dict],
    *,
    text_key: str = "text",
    other_share: float = DEFAULT_OTHER_CHAR_SHARE,
) -> pd.DataFrame:
    """Units whose share of ``other`` characters exceeds ``other_share``."""
    rows = []
    for u in units:
        text = str(u.get(text_key) or "")
        if not text:
            continue
        classes = Counter(_char_class(ch) for ch in text)
        share = classes.get("other", 0) / len(text)
        if share >= other_share:
            rows.append(
                {
                    "unit_id": u.get("unit_id"),
                    "doc_id": u.get("doc_id"),
                    "n_chars": len(text),
                    "other_share": share,
                    "n_other": int(classes.get("other", 0)),
                    "flag": "high_other_chars",
                }
            )
    return pd.DataFrame(rows)


def assess_text_report(
    units: Sequence[dict],
    *,
    text_key: str = "text",
    lang: LangHint = "auto",
) -> dict[str, pd.DataFrame]:
    """Bundle common Assess tables for notebooks (sizes, sentences, words, chars)."""
    sizes = unit_size_table(units, text_key=text_key)
    sent = sentence_length_table(units, text_key=text_key)
    words = word_length_table(units, text_key=text_key, lang=lang)
    return {
        "sizes": sizes,
        "size_summary": unit_length_summary(sizes),
        "unit_length_flags": flag_unit_length(units, text_key=text_key),
        "sentences": sent,
        "sentence_flags": flag_sentence_length(sent),
        "words": words,
        "word_flags": flag_word_length(words),
        "char_classes": character_inventory(units, text_key=text_key),
        "unusual_codepoints": unusual_codepoints(units, text_key=text_key),
        "char_flags": flag_unusual_characters(units, text_key=text_key),
        "empty": pd.DataFrame(
            {"unit_id": empty_unit_flags(units, text_key=text_key)}
        ),
    }
