"""End-to-end validation experiments (synthetic / FakeClient by default).

Runs extract → embed → cluster → lenses → document-weighted compare → multiverse.
Writes artefacts under a caller-chosen directory (use gitignored ``outputs/``).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .cluster import (
    Embedder,
    example_phrases_for_clusters,
    frozen_or_new_assignments,
    make_label_work,
    make_lens_work,
    resolve_lenses,
)
from .config import dump_json
from .dummy import BANK, FakeClient, make_units, write_units_json
from .extract import make_extract_work, phrase_table, yield_report
from .llm import StageRunner
from .multiverse import enumerate_configurations, run_multiverse, variance_decomposition
from .report import evidence_pack, write_findings, write_manifest
from .soft import soft_mapping_from_hard
from .subject_grain import lock_subject_grain
from .weight import group_compare, soft_group_compare

# Preferred municipal cycling framings for CIMT-style German corpora (notebook 09).
CYCLING_LENS_NAMES = (
    "Radwege und Führung",
    "Parken und Abstellen",
    "Fahrbahn und Oberfläche",
    "Knotenpunkte und Straßenbahn",
    "Zugang und Rheinufer",
    "Sicherheit im Mischverkehr",
)

CYCLING_LABEL_PROMPT = (
    "Beschrifte dieses Themencluster auf Deutsch. "
    "Return JSON with keys label and description. "
    "label: kurze deutsche Überschrift (höchstens sechs Wörter), kein Englisch. "
    "description: ein deutscher Satz.\n"
    "Phrases:\n<<PHRASES>>"
)

CYCLING_LENS_PROMPT = (
    "Return JSON with key lenses: a list of objects "
    "{name, description, clusters}. "
    "Prefer these German framing names when they fit (merge unused names; "
    "do not invent English names):\n"
    + "\n".join(f"- {n}" for n in CYCLING_LENS_NAMES)
    + "\n"
    "Group every cluster_id into exactly one lens. "
    "clusters must be an array of cluster_id integers "
    "from 0 to <<K_MINUS_1>> inclusive. "
    "Split parking from protected lanes; keep junction/tram risk separate "
    "from general path design when the phrases support it.\n"
    "<<CLUSTERS>>"
)


def gold_argument_format_compare(
    units: list[dict[str, Any]],
    *,
    formats: tuple[str, ...] | None = None,
    code_key: str = "code",
) -> pd.DataFrame:
    """Document-weighted major-position / premise shares by format (CIMT gold).

    Matches the Romberg & Conrad (2021) format contrast: dialogues are
    premise-rich; the Bonn survey is major-position-heavy. Units with
    ``meta.code`` in ``{mpos, premise, mpos+premise}`` contribute; ``non-arg``
    is dropped. ``mpos+premise`` counts toward both rates.
    """
    rows: list[dict[str, Any]] = []
    for u in units:
        code = (u.get("meta") or {}).get(code_key)
        if code in (None, "", "non-arg"):
            continue
        fmt = u.get("format") or u.get("group")
        if fmt is None:
            continue
        rows.append(
            {
                "doc_id": u["doc_id"],
                "format": str(fmt),
                "is_mpos": code in ("mpos", "mpos+premise"),
                "is_premise": code in ("premise", "mpos+premise"),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "metric",
                *[f"{f}_pct" for f in (formats or ())],
                "difference",
                "docs_a",
                "docs_b",
            ]
        )
    df = pd.DataFrame(rows)
    fmt_levels = list(formats) if formats else sorted(df["format"].unique())
    if len(fmt_levels) < 2:
        fmt_levels = sorted(df["format"].unique())
    g0, g1 = fmt_levels[0], fmt_levels[1]

    def _doc_means(mask_col: str) -> dict[str, Any]:
        doc = (
            df.groupby(["format", "doc_id"], as_index=False)[mask_col]
            .mean()
            .rename(columns={mask_col: "share"})
        )
        out: dict[str, Any] = {"metric": mask_col.replace("is_", "") + "_share"}
        means = {}
        counts = {}
        for f in (g0, g1):
            sub = doc[doc["format"] == f]["share"]
            means[f] = float(100 * sub.mean()) if len(sub) else float("nan")
            counts[f] = int(len(sub))
            out[f"{f}_pct"] = means[f]
            out[f"docs_{f}"] = counts[f]
        out["difference"] = means[g1] - means[g0]
        return out

    return pd.DataFrame([_doc_means("is_mpos"), _doc_means("is_premise")])


def run_validation_experiment(
    out_dir: str | Path,
    *,
    n_docs_per_group: int = 4,
    units_per_doc: int = 3,
    k: int = 4,
    seed: int = 0,
    quiet: bool = True,
) -> dict[str, Any]:
    """Run the synthetic pipeline. Returns a summary dict; writes files under ``out_dir``."""
    out = Path(out_dir)
    ckpt, logs, tables = out / "checkpoints", out / "logs", out / "tables"
    for d in (ckpt, logs, tables):
        d.mkdir(parents=True, exist_ok=True)

    units = make_units(n_docs_per_group=n_docs_per_group, units_per_doc=units_per_doc)
    write_units_json(units, out / "synthetic_units.json")
    units_by_id = {u["unit_id"]: u for u in units}

    client = FakeClient()
    runner = StageRunner(ckpt, logs, max_workers=2, sleep=lambda _: None)

    extraction: dict[str, dict] = {}
    for kind in ("concern", "benefit"):
        work = make_extract_work(
            client,
            kind=kind,
            system="extract",
            user_for_unit=lambda u, k=kind: u["text"],
            model="fake-small",
            sentinel=f"NO_{kind.upper()}",
            quote_threshold=0.8,
        )
        extraction[kind] = runner.run(
            f"extract_{kind}",
            units,
            lambda u: u["unit_id"],
            work,
            f"extract|{kind}|fake-small|v1",
            quiet=quiet,
        )

    phrases = phrase_table(
        extraction, units_by_id, kinds=["concern", "benefit"], extra_unit_fields=["group"]
    )
    # Prefer verified points when any exist
    verified = phrases[phrases.verified] if "verified" in phrases.columns else phrases
    if len(verified) < 4:
        verified = phrases
    verified = verified.reset_index(drop=True)
    verified.to_csv(tables / "phrases.csv", index=False)

    by_group = {
        g: [u["unit_id"] for u in units if u["group"] == g]
        for g in sorted({u["group"] for u in units})
    }
    yield_report(extraction, by_group, kinds=["concern", "benefit"]).to_csv(
        tables / "yield.csv", index=False
    )

    emb = Embedder(ckpt, client, "fake-embed")
    E = emb(verified.phrase.tolist())
    k_eff = min(k, max(2, len(verified) // 3))
    labels, centroids, frozen = frozen_or_new_assignments(
        verified, E, k_eff, seed, ckpt, replay=False
    )
    verified = verified.copy()
    verified["cluster"] = labels
    verified["centroid_sim"] = (E * centroids[labels]).sum(1)

    cluster_units = example_phrases_for_clusters(verified, k_eff, seed)
    lab = runner.run(
        f"cluster_labels_k{k_eff}",
        cluster_units,
        lambda cu: cu["key"],
        make_label_work(
            client,
            system="label",
            prompt_template="Label these:\n<<PHRASES>>",
            model="fake-small",
        ),
        f"labels|k{k_eff}|fake-small",
        quiet=quiet,
    )
    names = {
        cu["cluster"]: lab.get(cu["key"], {}).get("label", f"cluster {cu['cluster']}")
        for cu in cluster_units
    }
    verified["cluster_label"] = verified.cluster.map(names)

    cl_desc = "\n".join(
        f"{c}: {names[c]} | n_phrases={int((verified.cluster == c).sum())}"
        for c in range(k_eff)
    )
    lens_runs = runner.run(
        f"lenses_k{k_eff}",
        list(range(1, 3)),
        lambda r: str(r),
        make_lens_work(
            client,
            system="lens",
            prompt_template="Group:\n<<CLUSTERS>>",
            cluster_description=cl_desc,
            model="fake-small",
            k=k_eff,
        ),
        f"lenses|k{k_eff}|{cl_desc[:80]}",
        quiet=quiet,
    )
    lens_of, _ = resolve_lenses(k_eff, lens_runs)
    verified["lens"] = verified.cluster.map(lens_of)
    verified.to_csv(tables / "phrases_clustered.csv", index=False)

    rng = np.random.default_rng(seed)
    compare = group_compare(
        verified,
        "group",
        "lens",
        None,
        rng,
        reps=200,
        groups=sorted(verified.group.unique()),
    )
    compare.to_csv(tables / "group_compare_lenses.csv", index=False)

    def evaluate(cfg: dict) -> dict:
        # Simple synthetic ℓ: share of phrases in Lens A for group_a under cfg threshold
        sub = verified[verified.group == "group_a"]
        share = float((sub.lens == "Lens A").mean()) if len(sub) else 0.0
        return {"ell_lens_a": share + 0.01 * cfg["k"] + cfg["threshold"]}

    configs = enumerate_configurations({"k": [k_eff, k_eff + 1], "threshold": [0.4, 0.5]})
    multi = run_multiverse(configs, evaluate)
    multi.to_csv(tables / "multiverse.csv", index=False)
    shares = variance_decomposition(multi, "ell_lens_a", ["k", "threshold"])
    shares.to_csv(tables / "variance_shares.csv", index=False)

    evidence_pack(
        verified,
        out / "evidence_pack.html",
        group_col="group",
        title="Synthetic evidence pack",
        seed=seed,
    )
    summary = {
        "n_units": len(units),
        "n_phrases": len(verified),
        "k": k_eff,
        "frozen_clusters": frozen,
        "n_fake_calls": len(client.calls),
        "bank_kinds": list(BANK),
        "synthetic": True,
    }
    write_manifest(out / "run_manifest.json", summary)
    dump_json(summary, tables / "summary.json")
    return summary


FORMAT_PAIR = ("workshop", "survey")


def format_tagged_units(
    *,
    n_docs_per_group: int = 4,
    units_per_doc: int = 3,
    formats: tuple[str, ...] = FORMAT_PAIR,
) -> list[dict[str, Any]]:
    """Synthetic units with ``format`` as the group key (formats-style Address)."""
    units = make_units(
        n_docs_per_group=n_docs_per_group,
        units_per_doc=units_per_doc,
        groups=formats,
    )
    for u in units:
        u["format"] = u["group"]
        u["meta"] = {**(u.get("meta") or {}), "format": u["format"], "synthetic": True}
    return units


def load_cimt_format_pair(
    *,
    max_units_per: int = 80,
    dialogue_process: str = "Cycling-Dialogue-Bonn",
    survey_process: str = "Survey-Bonn",
) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    """Load CIMT dialogue vs survey as format-tagged units (Access demo).

    Returns ``(units, meta)``. On download/parse failure, ``units`` is ``None``
    and ``meta`` carries ``error``. German text needs a real LLM for extraction;
    use :func:`format_tagged_units` for the FakeClient Address path.
    """
    from .access import load

    meta: dict[str, Any] = {
        "dialogue_process": dialogue_process,
        "survey_process": survey_process,
        "source": "cimt",
    }
    try:
        dial = load("cimt", process=dialogue_process, max_units=max_units_per)
        surv = load("cimt", process=survey_process, max_units=max_units_per)
    except Exception as exc:  # network / cache / schema
        meta["error"] = str(exc)
        return None, meta

    units: list[dict[str, Any]] = []
    for bundle, fmt in ((dial, "dialogue"), (surv, "survey")):
        for u in bundle["units"]:
            row = dict(u)
            row["format"] = fmt
            row["group"] = fmt
            row["meta"] = {**(row.get("meta") or {}), "format": fmt, "cimt_process": fmt}
            units.append(row)
    meta.update(
        {
            "n_units": len(units),
            "n_dialogue": sum(1 for u in units if u["format"] == "dialogue"),
            "n_survey": sum(1 for u in units if u["format"] == "survey"),
            "n_docs": len({u["doc_id"] for u in units}),
        }
    )
    return units, meta


def run_formats_complexity_demo(
    out_dir: str | Path,
    *,
    units: list[dict[str, Any]] | None = None,
    client: Any | None = None,
    n_docs_per_group: int = 4,
    units_per_doc: int = 3,
    k: int = 5,
    lens_runs: int = 3,
    seed: int = 0,
    quiet: bool = True,
    include_soft: bool = True,
    include_distance: bool = True,
    kinds: tuple[str, ...] = ("concern", "benefit", "condition"),
    extract_model: str = "fake-small",
    embed_model: str = "fake-embed",
    label_model: str | None = None,
    max_workers: int = 2,
    extract_system: str = "extract",
    extract_user_for_unit: Any | None = None,
    label_prompt_template: str | None = None,
    lens_prompt_template: str | None = None,
    k_grid: list[int] | None = None,
    k_multiverse: str | list[int] | None = "hold",
    subject_grain_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Formats-style pipeline: format labels, hard+soft compare, EMD, format-gap ℓ.

    Default: English synthetic units + FakeClient (CI/Colab offline). Pass real
    ``units`` (e.g. CIMT format pair) and an ``OpenAIClient`` to run live; results
    resume from ``out_dir/checkpoints`` via StageRunner fingerprints — re-runs
    skip completed items until the fingerprint (prompt/model/version) changes.

    Optional ``label_prompt_template`` / ``lens_prompt_template`` override the
    default English JSON prompts (use :data:`CYCLING_LABEL_PROMPT` /
    :data:`CYCLING_LENS_PROMPT` for German municipal framings). Lens templates
    may include ``<<K_MINUS_1>>``, replaced with ``k_eff - 1``.

    Subject grain (CIP-0009): the factorial multiverse does **not** vary \(k\)
    by default. Pass an explicit ``k_grid`` for an optional one-factor
    resolution sweep only. ``subject_grain_lock`` (or an auto-built lock from
    ``k`` / ``k_multiverse``) is written into the run manifest for Address.

    Do not commit checkpoint JSONL that contains participant text; keep under
    gitignored ``outputs/``.
    """
    out = Path(out_dir)
    ckpt, logs, tables = out / "checkpoints", out / "logs", out / "tables"
    for d in (ckpt, logs, tables):
        d.mkdir(parents=True, exist_ok=True)

    if units is None:
        formats = FORMAT_PAIR
        units = format_tagged_units(
            n_docs_per_group=n_docs_per_group,
            units_per_doc=units_per_doc,
            formats=formats,
        )
        synthetic = True
    else:
        formats = tuple(sorted({str(u.get("format") or u.get("group")) for u in units}))
        if len(formats) < 2:
            formats = FORMAT_PAIR
        synthetic = False
    write_units_json(units, out / "format_units.json")
    units_by_id = {u["unit_id"]: u for u in units}

    gold_cmp = gold_argument_format_compare(units, formats=formats)
    if len(gold_cmp):
        gold_cmp.to_csv(tables / "gold_argument_format_compare.csv", index=False)

    client = client or FakeClient()
    label_model = label_model or extract_model
    if isinstance(client, FakeClient):
        runner = StageRunner(ckpt, logs, max_workers=max_workers, sleep=lambda _: None)
    else:
        runner = StageRunner(ckpt, logs, max_workers=max_workers)

    user_fn = extract_user_for_unit or (lambda u: u.get("extract_text") or u["text"])

    extraction: dict[str, dict] = {}
    for kind in kinds:
        def _user(u, k=kind, fn=user_fn, fake=isinstance(client, FakeClient)):
            body = fn(u)
            if fake:
                return body
            return f"Extract kind={k}. Reply with '- phrase || quote' lines or NO_{k.upper()}.\n\n{body}"

        work = make_extract_work(
            client,
            kind=kind,
            system=extract_system,
            user_for_unit=_user,
            model=extract_model,
            sentinel=f"NO_{kind.upper()}",
            quote_threshold=0.8,
        )
        extraction[kind] = runner.run(
            f"extract_{kind}",
            units,
            lambda u: u["unit_id"],
            work,
            f"extract|{kind}|{extract_model}|v1",
            quiet=quiet,
        )

    phrases = phrase_table(
        extraction,
        units_by_id,
        kinds=list(kinds),
        extra_unit_fields=["format", "group"],
    )
    verified = phrases[phrases.verified] if "verified" in phrases.columns else phrases
    if len(verified) < 6:
        verified = phrases
    verified = verified.reset_index(drop=True)
    verified.to_csv(tables / "phrases.csv", index=False)

    if "format" not in verified.columns and "group" in verified.columns:
        verified["format"] = verified["group"]
    by_format = {
        f: [u["unit_id"] for u in units if (u.get("format") or u.get("group")) == f]
        for f in formats
    }
    yield_report(extraction, by_format, kinds=list(kinds)).to_csv(
        tables / "yield.csv", index=False
    )

    emb = Embedder(ckpt, client, embed_model)
    E = emb(verified.phrase.tolist())
    k_eff = min(k, max(2, len(verified) // 3))
    labels, centroids, frozen = frozen_or_new_assignments(
        verified, E, k_eff, seed, ckpt, replay=False
    )
    verified = verified.copy()
    verified["cluster"] = labels
    verified["centroid_sim"] = (E * centroids[labels]).sum(1)

    cluster_units = example_phrases_for_clusters(verified, k_eff, seed)
    label_tmpl = label_prompt_template or (
        "Return JSON with keys label and description.\n"
        "Phrases:\n<<PHRASES>>"
    )
    lab = runner.run(
        f"cluster_labels_k{k_eff}",
        cluster_units,
        lambda cu: cu["key"],
        make_label_work(
            client,
            system="label",
            prompt_template=label_tmpl,
            model=label_model,
        ),
        f"labels|k{k_eff}|{label_model}|json-v3|{hash(label_tmpl) & 0xFFFF:x}",
        quiet=quiet,
    )
    names = {
        cu["cluster"]: lab.get(cu["key"], {}).get("label", f"cluster {cu['cluster']}")
        for cu in cluster_units
    }
    verified["cluster_label"] = verified.cluster.map(names)

    # Leading "{id}:" keeps FakeClient / parsers happy; n_phrases= is NOT a cluster id.
    cl_desc = "\n".join(
        f"{c}: {names[c]} | n_phrases={int((verified.cluster == c).sum())}"
        for c in range(k_eff)
    )
    n_lens_runs = max(2, lens_runs)
    lens_run_ids = list(range(1, n_lens_runs + 1))
    lens_tmpl = lens_prompt_template or (
        "Return JSON with key lenses: a list of objects "
        "{name, description, clusters}. "
        "Group every cluster_id into exactly one lens. "
        "clusters must be an array of cluster_id integers "
        "from 0 to <<K_MINUS_1>> inclusive.\n"
        "<<CLUSTERS>>"
    )
    lens_tmpl = lens_tmpl.replace("<<K_MINUS_1>>", str(k_eff - 1))
    lens_runs_raw = runner.run(
        f"lenses_k{k_eff}",
        lens_run_ids,
        lambda r: str(r),
        make_lens_work(
            client,
            system="lens",
            prompt_template=lens_tmpl,
            cluster_description=cl_desc,
            model=label_model,
            k=k_eff,
        ),
        f"lenses|k{k_eff}|{label_model}|lens-v4|{hash(lens_tmpl) & 0xFFFF:x}|{cl_desc[:60]}",
        quiet=quiet,
    )
    label_missing = runner.status.get(f"cluster_labels_k{k_eff}", {}).get("missing", [])
    lens_missing = runner.status.get(f"lenses_k{k_eff}", {}).get("missing", [])
    if label_missing or lens_missing:
        # Empty checkpoints leave default names / a single "Other" lens and
        # degenerate the soft σ² sweep — surface that clearly in the summary.
        pass
    lens_of, _ = resolve_lenses(k_eff, lens_runs_raw)
    verified["lens"] = verified.cluster.map(lens_of)
    verified.to_csv(tables / "phrases_clustered.csv", index=False)
    n_distinct_lenses = int(verified["lens"].nunique())

    rng = np.random.default_rng(seed)
    hard_cmp = group_compare(
        verified,
        "format",
        "lens",
        None,
        rng,
        reps=400,
        groups=list(formats),
    )
    hard_cmp.to_csv(tables / "group_compare_format_lenses.csv", index=False)

    soft_summary: dict[str, Any] = {"skipped": True}
    soft_W_by_rule: dict[str, tuple[np.ndarray, list[str]]] = {}
    soft_curve: pd.DataFrame | None = None
    if include_soft:
        try:
            from . import soft as ms

            mappings = []
            for rid in lens_run_ids:
                raw = lens_runs_raw.get(str(rid), {}).get("mapping") or {}
                hard = {int(c): L for c, L in raw.items()}
                for c in range(k_eff):
                    hard.setdefault(c, "Other")
                mappings.append(soft_mapping_from_hard(hard))
            sweep = ms.sigma2_sweep_select(centroids, mappings)
            soft_curve = pd.DataFrame(sweep["curve"])
            soft_curve.to_csv(tables / "sigma2_stability_curve.csv", index=False)
            sigma2 = float(sweep["sigma2_best"])
            n_lens = ms.mean_n_lenses(mappings)
            rules = {
                rule: float(ms.apply_sigma2_rule(rule, soft_curve, n_lens))
                for rule in ms.SIGMA2_RULES
            }
            pd.Series(rules, name="sigma2").to_csv(tables / "sigma2_rules.csv")
            soft_map = soft_mapping_from_hard(lens_of)
            for rule, s2 in rules.items():
                W_r, names_r = ms.compute_mixture_weights(centroids, soft_map, s2)
                soft_W_by_rule[rule] = (W_r, names_r)
            # Main soft compare uses σ²* (stability-selected)
            W, lens_names = ms.compute_mixture_weights(centroids, soft_map, sigma2)
            pd.DataFrame(W, columns=lens_names).to_csv(
                tables / "lens_mixture_weights.csv", index_label="cluster"
            )
            soft_cmp = soft_group_compare(
                verified,
                W,
                lens_names,
                "format",
                rng,
                groups=list(formats),
                reps=400,
            )
            soft_cmp.to_csv(tables / "soft_group_compare_format.csv", index=False)
            soft_summary = {
                "skipped": False,
                "sigma2_best": sigma2,
                "selection": sweep.get("selection"),
                "mean_emd": sweep.get("emd_best"),
                "rules": rules,
                "n_lenses": len(lens_names),
                "degenerate_single_lens": len(lens_names) < 2,
            }
            if soft_summary["degenerate_single_lens"]:
                soft_summary["hint"] = (
                    "Only one lens survived (often all clusters mapped to Other). "
                    "Check logs/*_errors.json for label/lens stage failures; "
                    "fix OpenAI json_mode prompts, then re-run so StageRunner "
                    "retries missing items from the empty checkpoint."
                )
        except Exception as exc:
            soft_summary = {"skipped": True, "error": str(exc)}
            soft_W_by_rule = {}

    distance_summary: dict[str, Any] = {"skipped": True}
    if include_distance:
        try:
            from . import distance as dd

            group_map = {
                d: verified.loc[verified.doc_id == d, "format"].iloc[0]
                for d in verified.doc_id.unique()
            }
            dist = dd.run_document_distance_analysis(
                verified,
                centroids,
                group_map,
                min_phrases=2,
                n_perm=99,
                seed=seed,
            )
            dist["pairwise"].to_csv(tables / "doc_distance_pairwise.csv", index=False)
            pm = dist["permanova"]
            distance_summary = {
                "skipped": False,
                "n_docs": len(dist["docs"]),
                "dropped_docs": dist.get("dropped_docs"),
                "permanova_R2": pm.get("R2"),
                "permanova_p": pm.get("p_value"),
            }
        except Exception as exc:
            distance_summary = {"skipped": True, "error": str(exc)}

    # Multiverse over *analytic decisions* reusable from this run (no new LLM calls).
    # ℓ = document-weighted format gap (group1 − group0) on the lens with largest |diff|.
    # CIP-0009: do **not** put a wide k grid in the factorial dims by default —
    # subject grain is locked Assess work; pass k_grid= for a one-factor sweep.
    g0, g1 = formats[0], formats[1]
    membership_levels = ["hard"] + (
        [f"soft:{r}" for r in soft_W_by_rule] if soft_W_by_rule else []
    )
    multi_dims = {
        "quote_threshold": [0.0, 0.7, 0.8],
        "kind_filter": ["all", "concern"],
        "membership": membership_levels,
    }

    def _subset(cfg: dict) -> pd.DataFrame:
        sub = verified
        thr = float(cfg["quote_threshold"])
        if thr > 0 and "quote_support" in sub.columns:
            sub = sub[sub["quote_support"].fillna(0) >= thr]
        if cfg["kind_filter"] != "all" and "kind" in sub.columns:
            sub = sub[sub["kind"] == cfg["kind_filter"]]
        return sub

    def format_gap_ell(cfg: dict) -> dict:
        sub = _subset(cfg)
        out: dict[str, Any] = {
            "ell_format_gap": float("nan"),
            "gap_lens": None,
            "n_phrases": int(len(sub)),
            "n_docs": int(sub["doc_id"].nunique()) if len(sub) else 0,
        }
        if len(sub) < 6 or sub["format"].nunique() < 2:
            return out
        local_rng = np.random.default_rng(seed + int(1000 * cfg["quote_threshold"]))
        mem = cfg["membership"]
        if mem == "hard":
            cmp = group_compare(
                sub, "format", "lens", None, local_rng, groups=[g0, g1], reps=200
            )
        else:
            rule = mem.split(":", 1)[1]
            W_r, names_r = soft_W_by_rule[rule]
            cmp = soft_group_compare(
                sub, W_r, names_r, "format", local_rng, groups=[g0, g1], reps=200
            )
        if cmp.empty or "difference" not in cmp.columns:
            return out
        row = cmp.loc[cmp["difference"].abs().idxmax()]
        out.update(
            {
                "ell_format_gap": float(row["difference"]),
                "gap_lens": str(row.get("lens", "")),
                f"{g0}_pct": float(row.get(f"{g0}_pct", float("nan"))),
                f"{g1}_pct": float(row.get(f"{g1}_pct", float("nan"))),
                "clear": bool(row.get("clear", False)),
            }
        )
        return out

    configs = enumerate_configurations(multi_dims)
    multi = run_multiverse(configs, format_gap_ell)
    multi.to_csv(tables / "multiverse_format_gap.csv", index=False)
    dim_cols = list(multi_dims)
    shares = variance_decomposition(multi.dropna(subset=["ell_format_gap"]), "ell_format_gap", dim_cols)
    shares.to_csv(tables / "variance_shares_format_gap.csv", index=False)

    # Optional one-factor resolution sweep (CIP-0009) — not part of factorial dims.
    resolution_sweep: pd.DataFrame | None = None
    if k_grid is not None:
        from .cluster import mppca_topics

        rows_k: list[dict[str, Any]] = []
        for k_try in [int(x) for x in k_grid]:
            k_try = min(k_try, max(2, len(verified) // 3))
            if k_try < 2:
                continue
            try:
                soft = mppca_topics(E, k_try, seed=seed)
                R_k = soft["responsibilities"]
                labels_k = soft["labels"]
                tmp = verified.copy()
                tmp["cluster"] = labels_k
                # Crude grain diagnostic: treat MAP topic as the category
                tmp["lens"] = tmp["cluster"].map(lambda c: f"topic_{int(c)}")
                local_rng = np.random.default_rng(seed + k_try)
                cmp_k = group_compare(
                    tmp, "format", "lens", None, local_rng, groups=[g0, g1], reps=100
                )
                ell = float("nan")
                if len(cmp_k) and "difference" in cmp_k.columns:
                    ell = float(cmp_k.loc[cmp_k["difference"].abs().idxmax(), "difference"])
                rows_k.append(
                    {
                        "k": k_try,
                        "ell_format_gap": ell,
                        "n_map": int(len(set(labels_k.tolist()))),
                        "mean_max_resp": float(R_k.max(axis=1).mean()),
                        "collapsed": bool(soft.get("collapsed", False)),
                    }
                )
            except Exception as exc:
                rows_k.append({"k": k_try, "ell_format_gap": float("nan"), "error": str(exc)})
        resolution_sweep = pd.DataFrame(rows_k)
        resolution_sweep.to_csv(tables / "resolution_k_sweep.csv", index=False)

    grain_lock = subject_grain_lock or lock_subject_grain(
        primary_k=k_eff,
        means=centroids,
        labels=labels,
        k_multiverse=(list(k_grid) if k_grid is not None else k_multiverse),
        extra={"source": "run_formats_complexity_demo"},
    )

    evidence_pack(
        verified,
        out / "evidence_pack.html",
        group_col="format",
        title="Formats-complexity evidence pack",
        seed=seed,
    )
    write_findings(
        verified,
        tables / "findings.md",
        compare=hard_cmp,
        multiverse=multi,
        variance_shares=shares,
        gold_compare=gold_cmp if len(gold_cmp) else None,
        group_col="format",
        title="Formats-complexity findings",
    )
    summary: dict[str, Any] = {
        "n_units": len(units),
        "n_phrases": len(verified),
        "k": k_eff,
        "formats": list(formats),
        "kinds": list(kinds),
        "lens_runs": n_lens_runs,
        "frozen_clusters": frozen,
        "extract_model": extract_model,
        "embed_model": embed_model,
        "n_client_calls": len(getattr(client, "calls", [])),
        "soft": soft_summary,
        "distance": distance_summary,
        "synthetic": synthetic,
        "checkpoint_dir": str(ckpt),
        "n_distinct_lenses": n_distinct_lenses,
        "label_stage_missing": label_missing,
        "lens_stage_missing": lens_missing,
        "gold_argument_rows": int(len(gold_cmp)),
        "analogy": "ai-dialogue-formats Address stack on public/synthetic stand-in",
        "subject_grain": grain_lock,
        "multiverse_dims": list(multi_dims),
        "resolution_k_sweep": (
            False if resolution_sweep is None else int(len(resolution_sweep))
        ),
    }
    write_manifest(out / "run_manifest.json", summary)
    dump_json(summary, tables / "summary.json")
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Run multilogue validation on synthetic units only.")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/validation_smoke"),
        help="Output directory (gitignored; default outputs/validation_smoke)",
    )
    p.add_argument("--quiet", action="store_true", default=True)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--formats-demo",
        action="store_true",
        help="Run formats-complexity demo instead of the basic smoke experiment",
    )
    args = p.parse_args(argv)
    if args.formats_demo:
        summary = run_formats_complexity_demo(args.out, quiet=not args.verbose)
    else:
        summary = run_validation_experiment(args.out, quiet=not args.verbose)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
