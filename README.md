# multilogue

Reusable Access → Assess → Address methodology for LLM-assisted analysis of public dialogue corpora.

This repository is governed with VibeSafe. Design precedes code:

| Layer | Question | Location |
|-------|----------|----------|
| **WHY** | Guiding principles | [`tenets/multilogue/`](tenets/multilogue/) |
| **WHAT** | Desired outcomes | [`requirements/`](requirements/) |
| **HOW** | Design | [`cip/cip0001.md`](cip/cip0001.md) |
| **DO** | Implementation tasks | [`backlog/`](backlog/) |

CIP-0001 defines the package boundaries relative to `ai-dialogue-formats` and `pub_dialogue`. CIP-0002 adds pods-style Access loaders for public civic corpora. Fynesse informs AAA philosophically; multilogue does not depend on fynesse at runtime.

## Install

```bash
pip install -e ".[dev]"
pytest
```

## Access: switchable public corpora

Load public civic text as `Unit` lists (pods-style named sources). Cache under `MULTILOGUE_DATAPATH` or `~/.cache/multilogue` (never committed). Set `MULTILOGUE_ACCESS_YES=1` to skip licence prompts in CI.

```python
from multilogue.access import list_sources, load

print(list_sources())
# ['synthetic', 'polis', 'gdn_cc', 'cdcp', 'cimt', 'decidim']

bundle = load("synthetic")
bundle = load("polis", conversation="vtaiwan.uberx", max_units=200)
bundle = load("gdn_cc", split="valid", max_units=500)
units = bundle["units"]  # citation/licence in bundle["citation"], bundle["license"]
```

| Source | Content |
|--------|---------|
| `synthetic` | In-memory dummy units (no download) |
| `polis` | Polis openData comments (CC BY 4.0) |
| `gdn_cc` | Grand Débat clarified units (FR) |
| `cdcp` | Cornell eRulemaking comments (EN) |
| `cimt` | German mobility participation sentences |
| `decidim` | Metadecidim proposals/comments CSV |

Study PDF/`.docx` parsers stay in consumer packages.

## Pedagogical notebooks

Colab-ready notebooks walk Access → Assess → Address with diagnostic plots
(synthetic data by default; optional public open-data loaders):

| Notebook | Topic |
|----------|--------|
| [00 Access](notebooks/00_access.ipynb) | Units and switchable sources |
| [01 Assess](notebooks/01_assess.ipynb) | Assess without the question |
| [02 Extract](notebooks/02_extract.ipynb) | Checkpoints and quote support |
| [03 Cluster](notebooks/03_cluster.ipynb) | Frozen k-means, lenses, PCA view |
| [04 Weight](notebooks/04_weight.ipynb) | Document weighting |
| [05 Multiverse](notebooks/05_multiverse.ipynb) | Variance shares |
| [06 Validate](notebooks/06_validate.ipynb) | κ, sheets, evidence pack |
| [07 End-to-end](notebooks/07_end_to_end.ipynb) | Synthetic smoke experiment |

See [SETUP.md](SETUP.md). Regenerate with `python scripts/build_notebooks.py`.

## Synthetic validation (no corpora in git)

```bash
pip install -e ".[dev]"
multilogue-validate --out outputs/validation_smoke --verbose
pytest tests/test_experiment.py tests/test_access.py tests/test_notebooks_smoke.py -q
```

Outputs go under gitignored `outputs/`. Downloads go under the Access cache, not the repo.

## Docs

- [Methodology](docs/methodology.md) — shared analytic method
- [Migration](docs/migration.md) — how consumers should depend on this package
- [SETUP.md](SETUP.md) — notebooks and Colab

## Non-goals

Multilogue does not ship PDF/`.docx` parsers, study prompts, grounds taxonomies, or paper headline metrics. Those stay in consumer packages. No private dialogue corpora are stored in git.
