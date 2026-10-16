# Cookbook: consumer package skeleton

A consumer is a small installable package that **depends on multilogue** and owns study I/O, prompts, and headline metrics.

## Recommended layout

```text
my_dialogue_study/
  pyproject.toml          # depends on multilogue
  README.md
  my_study/
    __init__.py
    access.py             # PDFs / exports → units
    assess.py             # question-agnostic quality
    address.py            # prompts, orchestration, ℓ
    prompts/              # versioned prompt text
  notebooks/              # paper figures (optional)
  tests/
```

## `pyproject.toml` (minimal)

```toml
[project]
name = "my-dialogue-study"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "multilogue @ git+https://github.com/mlatcl/multilogue.git",
  "pandas",
  "numpy",
]

[project.optional-dependencies]
dev = ["pytest", "matplotlib"]
```

## Boundary rules

| In multilogue | In your package |
|---------------|-----------------|
| `Unit` / `Phrase` contracts | Parsers for your files |
| `StageRunner`, extract/cluster/weight helpers | Prompt text and kind taxonomy |
| Multiverse enumerate + variance shares | ℓ callbacks and configs |
| Optional public `access.load` | Private corpora and licences |
| Evidence-pack HTML shell | Confidentiality / redaction policy |

## Smoke test pattern

```python
# tests/test_smoke_synthetic.py
from multilogue.access import load
from multilogue.experiment import run_validation_experiment
from pathlib import Path

def test_units_contract():
    units = load("synthetic", n_docs_per_group=1, units_per_doc=2)["units"]
    assert {"unit_id", "doc_id", "text"} <= set(units[0])

def test_pipeline(tmp_path):
    summary = run_validation_experiment(tmp_path, n_docs_per_group=2, units_per_doc=2, k=3, quiet=True)
    assert summary["synthetic"] is True
```

Use synthetic validation until your Access layer is ready. Never point CI at private dialogue paths.

## Next cookbooks

- [ai-dialogue-formats style](ai-dialogue-formats.md) — format comparison
- [pub-dialogue style](pub-dialogue.md) — multi-technology consultations
