# multilogue

Reusable Access → Assess → Address methodology for LLM-assisted analysis of public dialogue corpora.

This repository is governed with VibeSafe. Design precedes code:

| Layer | Question | Location |
|-------|----------|----------|
| **WHY** | Guiding principles | [`tenets/multilogue/`](tenets/multilogue/) |
| **WHAT** | Desired outcomes | [`requirements/`](requirements/) |
| **HOW** | Design | [`cip/cip0001.md`](cip/cip0001.md) |
| **DO** | Implementation tasks | [`backlog/`](backlog/) |

CIP-0001 defines the package boundaries relative to `ai-dialogue-formats` and `pub-dialogue`. Fynesse informs AAA philosophically; multilogue does not depend on fynesse at runtime.

## Install

```bash
pip install -e ".[dev]"
pytest
```

## Synthetic validation (no real dialogue data)

This repo must not contain participant transcripts or dialogue PDFs. Validation uses in-memory synthetic units:

```bash
pip install -e ".[dev]"
multilogue-validate --out outputs/validation_smoke --verbose
# or: python -m multilogue.experiment --out outputs/validation_smoke
pytest tests/test_experiment.py -q
```

Outputs go under gitignored `outputs/`. The phrase bank and `FakeClient` live in `multilogue/dummy.py`.

## Docs

- [Methodology](docs/methodology.md) — shared analytic method
- [Migration](docs/migration.md) — how `dialogue_formats` and `pub_dialogue` should depend on this package

## Non-goals

Multilogue does not ship PDF/`.docx` parsers, study prompts, grounds taxonomies, or paper headline metrics. Those stay in consumer packages. No real dialogue corpora are stored here.
