# Cookbook: building an `ai-dialogue-formats`-style package

Goal: a consumer that compares **dialogue formats** (how people were convened), using multilogue for shared stages while keeping format frames, experience coding, and format-gap ℓ local.

This page is a blueprint for recreating a package like [`mlatcl/ai-dialogue-formats`](https://github.com/mlatcl/ai-dialogue-formats) / `dialogue_formats`. It does **not** import that repo and uses only synthetic units.

For a **runnable end-to-end** demo of the same Address stack (format labels, soft compare, format-gap ℓ), see pedagogical notebook [09_formats_complexity](../../notebooks/09_formats_complexity.ipynb) (`run_formats_complexity_demo`). Access can use public CIMT dialogue vs survey; Address defaults to FakeClient, with an optional OpenAI path checkpointed under `outputs/`.

## What multilogue owns vs what you keep

| Concern | Call multilogue | Keep local |
|---------|-----------------|------------|
| Quote gate, hashing, JSON parse | `multilogue.text` | — |
| Stage runner / replay | `multilogue.llm.StageRunner` | OpenAI wiring if custom |
| Extract parse / yield | `multilogue.extract` | Format-specific `TYPES`, prompt renderers |
| Embed + frozen k-means + lenses | `multilogue.cluster` | Columns that name formats on tables |
| Doc weights, JSD, κ | `multilogue.weight` | Format-named wrappers |
| Multiverse grid | `multilogue.multiverse` | Experience-gap ℓ configs |
| Blind sheets / evidence pack | `multilogue.validate`, `report` | Grounds, own-words lists, confidentiality |

## Package sketch

```text
dialogue_formats/
  pyproject.toml              # depends on multilogue
  dialogue_formats/
    access.py                 # load format-tagged exports → units
    assess.py                 # thin: call assess_base + format coverage plots
    extract_types.py          # TYPES, render(unit, kind) → prompt
    pipeline.py               # Run orchestration
    compare.py                # format-gap ℓ for multiverse
    grounds.py                # study coding scheme
  notebooks/
```

### Access: attach a format label

```python
# dialogue_formats/access.py
from multilogue.access import load as public_load  # optional open data

def units_from_study_table(df) -> list[dict]:
    """df has columns: unit_id, doc_id, text, format."""
    return [
        {
            "unit_id": str(r.unit_id),
            "doc_id": str(r.doc_id),
            "text": str(r.text),
            "extract_text": str(r.text),
            "format": str(r.format),  # group key for later compare
            "meta": {"format": str(r.format)},
        }
        for r in df.itertuples()
    ]

def demo_units():
    """CI / docs path — no personal data."""
    bundle = public_load("synthetic", n_docs_per_group=3, units_per_doc=3)
    # Map synthetic group_a/group_b → pretend formats
    out = []
    for u in bundle["units"]:
        u = dict(u)
        u["format"] = "workshop" if u["group"] == "group_a" else "survey"
        out.append(u)
    return out
```

### Extract: study prompts, shared runner

```python
# dialogue_formats/pipeline.py (excerpt)
from pathlib import Path
from multilogue.extract import make_extract_work, phrase_table
from multilogue.llm import StageRunner

def run_extract(units, client, root: Path, system: str, model: str):
    runner = StageRunner(root / "ckpt", root / "logs")
    units_by_id = {u["unit_id"]: u for u in units}
    extraction = {}
    for kind in ("concern", "benefit", "condition"):
        work = make_extract_work(
            client,
            kind=kind,
            system=system,
            user_for_unit=lambda u, k=kind: render_prompt(u, k),  # your renderer
            model=model,
            sentinel=f"NO_{kind.upper()}",
            quote_threshold=0.8,
        )
        extraction[kind] = runner.run(
            f"extract_{kind}", units, lambda u: u["unit_id"], work,
            f"extract|{kind}|{model}|v1",
        )
    return phrase_table(
        extraction, units_by_id,
        kinds=list(extraction),
        extra_unit_fields=["format"],
    )
```

### Address: compare formats with document weights

```python
import numpy as np
from multilogue.weight import group_compare

def format_lens_compare(phrases, rng):
    return group_compare(
        phrases, group_col="format", col="lens", values=None, rng=rng,
        groups=sorted(phrases["format"].dropna().unique()),
    )
```

### Multiverse: format-gap ℓ stays yours

```python
from multilogue.multiverse import enumerate_configurations, run_multiverse, variance_decomposition

def experience_gap_ell(phrases_by_cfg) -> float:
    """Study-specific: e.g. difference in experience-coded share across formats."""
    ...

dims = {"k": [5, 6, 7], "quote_threshold": [0.7, 0.8]}
configs = enumerate_configurations(dims)

def evaluate(cfg):
    # run frozen pipeline under cfg → phrases → return {"ell": experience_gap_ell(...)}
    return {"ell": 0.0}  # placeholder for docs

# results = run_multiverse(configs, evaluate)
# shares = variance_decomposition(results, "ell", list(dims))
```

## Migration tip

While thinning an existing `dialogue_formats` tree, re-export from multilogue so notebooks keep working:

```python
# dialogue_formats/text.py during transition
from multilogue.text import quote_support, sha, parse_json, get_list  # noqa: F401
```

See also [Migration](../migration.md).
