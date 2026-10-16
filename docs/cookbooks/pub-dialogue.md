# Cookbook: building a `pub-dialogue`-style package

Goal: a consumer for **multi-technology public consultations** (PDF-heavy Access, concern/benefit Address, paper-specific robustness and temporal ℓ), using multilogue for shared primitives.

Blueprint for a package like [`mlatcl/pub-dialogue`](https://github.com/mlatcl/pub-dialogue). Synthetic data only on this page.

## What multilogue owns vs what you keep

| Concern | Call multilogue | Keep local |
|---------|-----------------|------------|
| Stage runner / clients | `StageRunner`, `LiteLLMClient` / `OpenAIClient` | `AccessStage` PDF chunking, licences |
| Yield / phrase tables | `extract.yield_report`, `phrase_table` | Tech-term filters, concern/benefit prompts |
| Clustering helpers | `multilogue.cluster` | Soft PPCA lens memberships, σ² sweeps, orchestration |
| Multiverse | `enumerate_configurations`, `variance_decomposition` | R1–R3 ℓ, artefact loading |
| Evidence pack | `multilogue.report` | Study columns, quote policy |
| Assess size tables | `assess_base` | Bibliography / table-row heuristics |
| — | — | `crosscut`, distance / EMD, temporal analyses |

## Package sketch (Fynesse-shaped)

```text
pub_dialogue/
  pyproject.toml
  _config.yml                 # project overrides
  pub_dialogue/
    access.py                 # PDF → chunks → units (+ optional public_load)
    assess.py                 # quality flags, call assess_base
    address.py                # prompts, cluster orchestration, ℓ
    config.py                 # layered YAML if you use fynesse-style config
  notebooks/                  # 01_processing … paper figures
  tests/
```

### Access: PDFs locally, public loaders optional

```python
# pub_dialogue/access.py
from pathlib import Path
from multilogue.access import load as public_load

def units_from_pdf_dir(pdf_dir: Path, technology: str) -> list[dict]:
    units = []
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        for i, chunk in enumerate(chunk_pdf(pdf)):  # your parser
            units.append({
                "unit_id": f"{pdf.stem}-{i}",
                "doc_id": pdf.stem,
                "text": chunk["text"],
                "extract_text": chunk["text"],
                "technology": technology,
                "meta": {"page": chunk.get("page"), "technology": technology},
            })
    return units

def demo_units():
    """Docs/CI: map synthetic groups to pretend technologies."""
    units = public_load("synthetic", n_docs_per_group=4, units_per_doc=3)["units"]
    out = []
    for u in units:
        u = dict(u)
        u["technology"] = "tech_x" if u["group"] == "group_a" else "tech_y"
        out.append(u)
    return out
```

### Assess: question-agnostic first

```python
# pub_dialogue/assess.py
from multilogue.assess_base import unit_size_table, docs_per_group, empty_unit_flags

def assess_units(units):
    return {
        "sizes": unit_size_table(units),
        "docs": docs_per_group(units, "technology"),
        "too_short": empty_unit_flags(units, min_words=4),
        # plus your bibliography / table-row flags — still question-agnostic
    }
```

### Address: orchestrate multilogue, keep PPCA/ℓ local

```python
# pub_dialogue/address.py (orchestration sketch)
from pathlib import Path
import numpy as np
from multilogue.extract import make_extract_work, phrase_table
from multilogue.llm import StageRunner
from multilogue.cluster import Embedder, frozen_or_new_assignments, resolve_lenses
from multilogue.weight import group_compare
from multilogue.multiverse import enumerate_configurations, run_multiverse, variance_decomposition

def run_core(units, client, root: Path, prompts: dict, model: str, k: int):
    runner = StageRunner(root / "ckpt", root / "logs")
    units_by_id = {u["unit_id"]: u for u in units}
    extraction = {}
    for kind in ("concern", "benefit"):
        work = make_extract_work(
            client, kind=kind, system=prompts[kind],
            user_for_unit=lambda u: u["text"], model=model,
            sentinel=f"NO_{kind.upper()}",
        )
        extraction[kind] = runner.run(
            f"extract_{kind}", units, lambda u: u["unit_id"], work,
            f"extract|{kind}|{model}",
        )
    phrases = phrase_table(
        extraction, units_by_id, kinds=["concern", "benefit"],
        extra_unit_fields=["technology"],
    )
    E = np.asarray(Embedder(root / "emb", client, model)(phrases.phrase.tolist()), float)
    labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / "clusters")
    phrases = phrases.assign(cluster=labels, centroid_sim=(E * centroids[labels]).sum(1))
    # lenses via make_lens_work + resolve_lenses (blind), then optionally soft PPCA locally
    return phrases

def technology_compare(phrases, rng):
    return group_compare(
        phrases, "technology", "lens", None, rng,
        groups=sorted(phrases.technology.unique()),
    )

def robustness_ell(cfg) -> dict:
    """Paper metric — lives here, not in multilogue."""
    return {"ell": 0.0}
```

### Multiverse callback

```python
dims = {"k": [6, 8, 10], "prompt_set": ["A", "B"]}
configs = enumerate_configurations(dims)
# results = run_multiverse(configs, lambda cfg: run_and_score(cfg))
# shares = variance_decomposition(results, "ell", list(dims))
```

## AAA discipline

Keep PDF chunking and licence notes in Access. Keep bibliography heuristics in Assess. Put tech-term filters and PPCA soft memberships in Address — they encode the question. That split is what makes multilogue reusable across technologies and formats.

See [Migration](../migration.md) for a module-by-module thinning map.
