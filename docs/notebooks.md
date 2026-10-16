# Pedagogical notebooks

Colab-ready notebooks walk Access → Assess → Address. They follow a **talk
notebook** style: methodological prose and equations first, then separate cells
for library imports, computation, and figures, with interpretive markdown after
each visualisation.

Default path: **synthetic units + FakeClient** (no API key). Soft / formats
notebooks install `pot` when missing. Optional live LLM cells run only when
`OPENAI_API_KEY` is set.

| Notebook | Topic |
|----------|--------|
| [00 Access](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/00_access.ipynb) | Units and switchable sources |
| [01 Assess](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/01_assess.ipynb) | Assess without the question |
| [02 Extract](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/02_extract.ipynb) | Checkpoints and quote support |
| [03 Cluster](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/03_cluster.ipynb) | Frozen *k*-means, lenses, PCA view |
| [04 Weight](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/04_weight.ipynb) | Document weighting |
| [05 Multiverse](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/05_multiverse.ipynb) | Variance shares for consumer $\ell$ |
| [06 Validate](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/06_validate.ipynb) | $\kappa$, sheets, evidence pack |
| [07 End-to-end](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/07_end_to_end.ipynb) | Synthetic smoke experiment |
| [08 Soft / EMD](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/08_soft_distance.ipynb) | Mixture responsibilities, $\sigma^2$-by-EMD, document EMD |
| [09 Formats complexity](https://colab.research.google.com/github/mlatcl/multilogue/blob/main/notebooks/09_formats_complexity.ipynb) | Format as group; format-gap $\ell$; optional live LLM |

Regenerate from the builder (do not hand-edit generated notebooks):

```bash
python scripts/build_notebooks.py
pytest tests/test_notebooks_smoke.py -q
```

See [SETUP.md](https://github.com/mlatcl/multilogue/blob/main/SETUP.md) in the repository root.
