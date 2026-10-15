# Setup — pedagogical notebooks

## Local

```bash
pip install -e ".[dev]"
python scripts/build_notebooks.py   # regenerate notebooks/ from the builder
jupyter notebook notebooks/00_access.ipynb
# or: pytest tests/test_notebooks_smoke.py -q
```

## Colab

Each notebook has an **Open in Colab** badge. The setup cell installs multilogue from
`https://github.com/lawrennd/multilogue` (public) and matplotlib. No GitHub token is
required for the package itself.

| Notebook | Topic |
|----------|--------|
| [00_access](notebooks/00_access.ipynb) | Unit contract, switchable public sources |
| [01_assess](notebooks/01_assess.ipynb) | Assess without the question |
| [02_extract](notebooks/02_extract.ipynb) | Extraction, checkpoints, quote support |
| [03_cluster](notebooks/03_cluster.ipynb) | Frozen k-means, blind labels, PCA view |
| [04_weight](notebooks/04_weight.ipynb) | Document weighting |
| [05_multiverse](notebooks/05_multiverse.ipynb) | Multiverse variance shares |
| [06_validate](notebooks/06_validate.ipynb) | κ, sheets, evidence pack |
| [07_end_to_end](notebooks/07_end_to_end.ipynb) | Synthetic smoke experiment |

Default path: **synthetic units + FakeClient** (no API key). Optional cells load public
open data (e.g. Polis) into a local cache — never commit that cache.

## Regenerating notebooks

Edit `scripts/build_notebooks.py`, then run it. Do not hand-edit `notebooks/*.ipynb`
unless you are only changing outputs; prose and code cells are generated.
