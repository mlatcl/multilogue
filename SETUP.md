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
`https://github.com/mlatcl/multilogue` (public) and matplotlib. No GitHub token is
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
| [08_soft_distance](notebooks/08_soft_distance.ipynb) | Soft PPCA, σ²-by-EMD, document EMD (`pot`) |
| [09_formats_complexity](notebooks/09_formats_complexity.ipynb) | Formats-style stack; CIMT Access; optional live LLM via `.env` |

Corpus: public CIMT (or other Access sources). Labels / embeds / extract use
**OpenAI from the repo-root `.env`** when `OPENAI_API_KEY` is set (also found
when the notebook cwd is `notebooks/`). Offline FakeClient only when you set
`MULTILOGUE_FORCE_FAKE=1` — missing keys no longer fall through silently.

From the **repo root** (not `notebooks/`): `cp .env.example .env` and set
`OPENAI_API_KEY`. Install `pip install -e '.[openai,distance]'`. Checkpoints stay
under gitignored `outputs/` (do not commit JSONL with unit text).

## Regenerating notebooks

Edit `scripts/build_notebooks.py`, then run it. Do not hand-edit `notebooks/*.ipynb`
unless you are only changing outputs; prose and code cells are generated.
