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


def cluster_catalogue(
    phrases: pd.DataFrame,
    *,
    cluster_col: str = "cluster",
    label_col: str = "cluster_label",
    lens_col: str = "lens",
    phrase_col: str = "phrase",
    kind_col: str = "kind",
    n_examples: int = 4,
) -> pd.DataFrame:
    """One row per cluster: label, lens, counts, example phrases."""
    rows = []
    for c, sub in phrases.groupby(cluster_col, sort=True):
        label = sub[label_col].iloc[0] if label_col in sub.columns else f"cluster {c}"
        lens = sub[lens_col].iloc[0] if lens_col in sub.columns else ""
        kinds = (
            sub[kind_col].value_counts().to_dict() if kind_col in sub.columns else {}
        )
        # Prefer high centroid_sim examples when available
        ordered = (
            sub.sort_values("centroid_sim", ascending=False)
            if "centroid_sim" in sub.columns
            else sub
        )
        examples = "; ".join(ordered[phrase_col].head(n_examples).astype(str).tolist())
        rows.append(
            {
                "cluster": int(c) if str(c).isdigit() or isinstance(c, (int, float)) else c,
                "label": label,
                "lens": lens,
                "n": len(sub),
                "kinds": ", ".join(f"{k}:{v}" for k, v in kinds.items()),
                "examples": examples,
            }
        )
    return pd.DataFrame(rows)


def top_phrases_by_group(
    phrases: pd.DataFrame,
    *,
    kind: str | None = "concern",
    group_col: str = "format",
    phrase_col: str = "phrase",
    kind_col: str = "kind",
    n: int = 8,
) -> dict[str, pd.DataFrame]:
    """Top phrases per group (by centroid_sim when present), optionally filtered by kind."""
    df = phrases
    if kind is not None and kind_col in df.columns:
        df = df[df[kind_col] == kind]
    out: dict[str, pd.DataFrame] = {}
    if group_col not in df.columns:
        return out
    for g, sub in df.groupby(group_col):
        ordered = (
            sub.sort_values("centroid_sim", ascending=False)
            if "centroid_sim" in sub.columns
            else sub
        )
        cols = [c for c in [phrase_col, "cluster_label", "lens", "quote"] if c in ordered.columns]
        out[str(g)] = ordered[cols].head(n).reset_index(drop=True)
    return out


def format_contrast_bullets(
    compare: pd.DataFrame,
    *,
    group_a: str,
    group_b: str,
    label_col: str = "lens",
) -> list[str]:
    """Human-readable bullets from a hard/soft ``group_compare`` table."""
    a_pct, b_pct = f"{group_a}_pct", f"{group_b}_pct"
    if a_pct not in compare.columns or b_pct not in compare.columns:
        return []
    bullets = []
    for r in compare.itertuples():
        label = getattr(r, label_col)
        pa, pb = float(getattr(r, a_pct)), float(getattr(r, b_pct))
        clear = bool(getattr(r, "clear", False)) if "clear" in compare.columns else False
        diff = pb - pa
        direction = (
            f"**{group_b}** higher (+{diff:.0f} pp)"
            if diff > 0
            else f"**{group_a}** higher (+{-diff:.0f} pp)"
        )
        flag = " — clear gap" if clear else ""
        bullets.append(
            f"- **{label}**: {group_a} {pa:.0f}% vs {group_b} {pb:.0f}% "
            f"({direction}){flag}"
        )
    return bullets


def findings_markdown(
    phrases: pd.DataFrame,
    *,
    compare: pd.DataFrame | None = None,
    multiverse: pd.DataFrame | None = None,
    variance_shares: pd.DataFrame | None = None,
    group_col: str = "format",
    groups: Sequence[str] | None = None,
    title: str = "Findings",
    n_examples: int = 4,
    n_top: int = 6,
) -> str:
    """Narrative markdown: yield, clusters, concerns, format contrasts, multiverse."""
    groups = list(groups or (
        sorted(phrases[group_col].dropna().unique())
        if group_col in phrases.columns
        else []
    ))
    lines = [f"# {title}", ""]
    n = len(phrases)
    lines.append(f"**{n} phrases** across **{phrases['doc_id'].nunique() if 'doc_id' in phrases.columns else '?'} documents**.")
    if "kind" in phrases.columns:
        kind_bits = ", ".join(
            f"{k} {v}" for k, v in phrases["kind"].value_counts().items()
        )
        lines.append(f"By kind: {kind_bits}.")
    if group_col in phrases.columns:
        g_bits = ", ".join(
            f"{g} {v}" for g, v in phrases[group_col].value_counts().items()
        )
        lines.append(f"By {group_col}: {g_bits}.")
    lines.append("")

    cat = cluster_catalogue(phrases, n_examples=n_examples)
    lines.append("## Clusters")
    lines.append("")
    lines.append(
        "Each cluster is a topic bag from frozen *k*-means; labels are model-proposed."
    )
    lines.append("")
    for r in cat.itertuples():
        lines.append(f"### {r.cluster}. {r.label}")
        lines.append(f"- Lens: *{r.lens}* · {r.n} phrases ({r.kinds})")
        lines.append(f"- Examples: {r.examples}")
        lines.append("")

    if "kind" in phrases.columns and (phrases["kind"] == "concern").any():
        lines.append("## Concerns (by format)")
        lines.append("")
        tops = top_phrases_by_group(phrases, kind="concern", group_col=group_col, n=n_top)
        for g, tab in tops.items():
            lines.append(f"### {g}")
            for row in tab.itertuples():
                lab = getattr(row, "cluster_label", "")
                lab_bit = f" — *{lab}*" if lab else ""
                lines.append(f"- {getattr(row, 'phrase')}{lab_bit}")
            lines.append("")

    if "kind" in phrases.columns and (phrases["kind"] == "benefit").any():
        lines.append("## Benefits (by format)")
        lines.append("")
        tops = top_phrases_by_group(phrases, kind="benefit", group_col=group_col, n=max(4, n_top // 2))
        for g, tab in tops.items():
            lines.append(f"### {g}")
            for row in tab.itertuples():
                lines.append(f"- {getattr(row, 'phrase')}")
            lines.append("")

    if compare is not None and len(groups) >= 2:
        lines.append("## Format contrast (document-weighted lens shares)")
        lines.append("")
        bullets = format_contrast_bullets(
            compare, group_a=groups[0], group_b=groups[1]
        )
        if bullets:
            lines.extend(bullets)
            clear_n = int(compare["clear"].sum()) if "clear" in compare.columns else 0
            lines.append("")
            lines.append(
                f"{clear_n} of {len(compare)} lenses show a clear document-weighted gap "
                f"(bootstrap interval excludes zero and |diff| ≥ threshold)."
            )
        lines.append("")
        lines.append(
            "*Caveat:* this is a small public stand-in corpus; treat gaps as "
            "method demos, not policy findings."
        )
        lines.append("")

    if "lens" in phrases.columns:
        lines.append("## Lens × format phrase counts")
        lines.append("")
        ct = pd.crosstab(phrases["lens"], phrases[group_col]) if group_col in phrases.columns else phrases["lens"].value_counts()
        lines.append("```")
        lines.append(ct.to_string())
        lines.append("```")
        lines.append("")

    if variance_shares is not None and len(variance_shares):
        lines.append("## Multiverse — which decisions move ℓ?")
        lines.append("")
        lines.append(
            "ℓ is the document-weighted format gap (group₂ − group₁) on the lens "
            "with largest |difference|, recomputed under each analytic configuration "
            "(no new LLM calls)."
        )
        lines.append("")
        for r in variance_shares.itertuples():
            lines.append(
                f"- **{r.dimension}**: {100 * float(r.variance_share):.1f}% of "
                f"ℓ variance across the grid"
            )
        lines.append("")
        if multiverse is not None and "ell_format_gap" in multiverse.columns:
            m = multiverse.dropna(subset=["ell_format_gap"])
            if len(m):
                lo, hi = float(m.ell_format_gap.min()), float(m.ell_format_gap.max())
                lines.append(
                    f"Across {len(m)} configurations, ℓ ranges from "
                    f"**{lo:.1f}** to **{hi:.1f}** percentage points."
                )
                if "gap_lens" in m.columns:
                    top_lens = m["gap_lens"].value_counts().head(3)
                    lines.append(
                        "Most often the largest gap is on: "
                        + ", ".join(f"{a} ({b})" for a, b in top_lens.items())
                    )
                lines.append("")

    return "\n".join(lines)


def write_findings(
    phrases: pd.DataFrame,
    path: str | Path,
    *,
    compare: pd.DataFrame | None = None,
    multiverse: pd.DataFrame | None = None,
    variance_shares: pd.DataFrame | None = None,
    group_col: str = "format",
    title: str = "Findings",
) -> Path:
    """Write ``findings.md`` (and ``cluster_catalogue.csv`` beside it)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    groups = (
        sorted(phrases[group_col].dropna().unique())
        if group_col in phrases.columns
        else []
    )
    md = findings_markdown(
        phrases,
        compare=compare,
        multiverse=multiverse,
        variance_shares=variance_shares,
        group_col=group_col,
        groups=groups,
        title=title,
    )
    path.write_text(md, encoding="utf-8")
    cluster_catalogue(phrases).to_csv(
        path.with_name("cluster_catalogue.csv"), index=False
    )
    return path
