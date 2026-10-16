# Getting started

## Install

```bash
git clone https://github.com/mlatcl/multilogue.git
cd multilogue
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional extras:

| Extra | Adds |
|-------|------|
| `[report]` | matplotlib diagnostics (`multilogue.viz`) |
| `[openai]` / `[litellm]` | real model clients |
| `[docs]` | MkDocs Material + mkdocstrings |

## Five-minute synthetic run

No API key. No download.

```python
from multilogue.access import load
from multilogue.assess_base import unit_size_table, docs_per_group
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table
from multilogue.llm import StageRunner
from pathlib import Path

units = load("synthetic", n_docs_per_group=3, units_per_doc=3)["units"]
print(unit_size_table(units).describe())
print(docs_per_group(units, "group"))

client = FakeClient()
runner = StageRunner(Path("outputs/ckpt"), Path("outputs/logs"), max_workers=2, sleep=lambda _: None)
units_by_id = {u["unit_id"]: u for u in units}

extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client,
        kind=kind,
        system="extract",
        user_for_unit=lambda u: u["text"],
        model="fake-small",
        sentinel=f"NO_{kind.upper()}",
    )
    extraction[kind] = runner.run(
        f"extract_{kind}", units, lambda u: u["unit_id"], work, f"extract|{kind}", quiet=True
    )

phrases = phrase_table(extraction, units_by_id, kinds=["concern", "benefit"], extra_unit_fields=["group"])
print(phrases.head())
```

Or one shot:

```bash
multilogue-validate --out outputs/validation_smoke --verbose
```

## Build these docs

```bash
pip install -e ".[docs]"
mkdocs serve          # http://127.0.0.1:8000
mkdocs build --strict
```

## Next

- Learn the [methodology](methodology.md)
- Follow a [cookbook](cookbooks/consumer-skeleton.md) to create your study package
- Open a [Colab notebook](notebooks.md) for plots and pedagogy
