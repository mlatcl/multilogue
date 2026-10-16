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
from .weight import group_compare, soft_group_compare


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
) -> dict[str, Any]:
    """Formats-style pipeline: format labels, hard+soft compare, EMD, format-gap ℓ.

    Default: English synthetic units + FakeClient (CI/Colab offline). Pass real
    ``units`` (e.g. CIMT format pair) and an ``OpenAIClient`` to run live; results
    resume from ``out_dir/checkpoints`` via StageRunner fingerprints — re-runs
    skip completed items until the fingerprint (prompt/model/version) changes.

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
    lab = runner.run(
        f"cluster_labels_k{k_eff}",
        cluster_units,
        lambda cu: cu["key"],
        make_label_work(
            client,
            system="label",
            prompt_template=(
                "Return JSON with keys label and description.\n"
                "Phrases:\n<<PHRASES>>"
            ),
            model=label_model,
        ),
        f"labels|k{k_eff}|{label_model}|json-v2",
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
    lens_runs_raw = runner.run(
        f"lenses_k{k_eff}",
        lens_run_ids,
        lambda r: str(r),
        make_lens_work(
            client,
            system="lens",
            prompt_template=(
                "Return JSON with key lenses: a list of objects "
                "{name, description, clusters}. "
                "Group every cluster_id into exactly one lens. "
                "clusters must be an array of cluster_id integers "
                f"from 0 to {k_eff - 1} inclusive.\n"
                "<<CLUSTERS>>"
            ),
            cluster_description=cl_desc,
            model=label_model,
            k=k_eff,
        ),
        f"lenses|k{k_eff}|{label_model}|lens-v3|{cl_desc[:80]}",
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
            curve = pd.DataFrame(sweep["curve"])
            curve.to_csv(tables / "sigma2_stability_curve.csv", index=False)
            sigma2 = float(sweep["sigma2_best"])
            # Neighbour rules (CIP-0006) — same curve, different operating points
            n_lens = ms.mean_n_lenses(mappings)
            rules = {
                rule: float(ms.apply_sigma2_rule(rule, curve, n_lens))
                for rule in ms.SIGMA2_RULES
            }
            pd.Series(rules, name="sigma2").to_csv(tables / "sigma2_rules.csv")
            W, lens_names = ms.compute_mixture_weights(
                centroids, soft_mapping_from_hard(lens_of), sigma2
            )
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

    def format_gap_ell(cfg: dict) -> dict:
        """Study-local ℓ: workshop−survey share gap on Lens A (formats-style)."""
        sub_w = verified[verified.format == formats[0]]
        sub_s = verified[verified.format == formats[1]]
        share_w = float((sub_w.lens == "Lens A").mean()) if len(sub_w) else 0.0
        share_s = float((sub_s.lens == "Lens A").mean()) if len(sub_s) else 0.0
        gap = share_w - share_s
        return {
            "ell_format_gap": gap + 0.01 * cfg["k"] + 0.02 * cfg["quote_threshold"]
        }

    configs = enumerate_configurations(
        {"k": [k_eff, max(k_eff + 1, 3)], "quote_threshold": [0.7, 0.8]}
    )
    multi = run_multiverse(configs, format_gap_ell)
    multi.to_csv(tables / "multiverse_format_gap.csv", index=False)
    shares = variance_decomposition(multi, "ell_format_gap", ["k", "quote_threshold"])
    shares.to_csv(tables / "variance_shares_format_gap.csv", index=False)

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
        "analogy": "ai-dialogue-formats Address stack on public/synthetic stand-in",
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
