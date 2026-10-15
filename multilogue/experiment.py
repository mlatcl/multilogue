"""End-to-end validation experiment on synthetic units only.

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
from .report import evidence_pack, write_manifest
from .weight import group_compare


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
        f"{c}: {names[c]} — ({int((verified.cluster == c).sum())})" for c in range(k_eff)
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
    args = p.parse_args(argv)
    summary = run_validation_experiment(args.out, quiet=not args.verbose)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
