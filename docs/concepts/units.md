# Units and phrases

## Unit

A **unit** is one analysable text span. Multilogue never opens your PDFs; your Access layer produces units.

Required fields:

| Field | Meaning |
|-------|---------|
| `unit_id` | Stable unique id |
| `doc_id` | Document (or conversation) the unit belongs to |
| `text` | Analysable text |

Common optional fields:

| Field | Meaning |
|-------|---------|
| `extract_text` | Text the quote must support (defaults to `text`) |
| `context` | Surrounding material for humans / models |
| `meta` | Free-form dict (technology, format, period, …) |

Extra keys (e.g. `group`, `format`, `technology`) are allowed; pass their names into `phrase_table(..., extra_unit_fields=[...])` so they survive into Address tables.

```python
from multilogue.protocols import Unit

u: Unit = {
    "unit_id": "u0001",
    "doc_id": "doc_a",
    "text": "I worry that my data could be sold without consent.",
    "extract_text": "I worry that my data could be sold without consent.",
    "meta": {"synthetic": True},
}
```

## Phrase

A **phrase** is one extracted point attached to a unit (concern, benefit, condition, …).

| Field | Meaning |
|-------|---------|
| `phrase_id` | Stable id (`kind|unit_id|i` from `phrase_table`) |
| `kind` | Extraction pass name |
| `phrase` | Short point |
| `quote` | Supporting span from the unit |
| `quote_support` | Score from `quote_support(quote, source)` |
| `verified` | Passed the quote threshold |

## Synthetic source of truth for demos

`multilogue.dummy.make_units` and `FakeClient` invent short civic-style sentences in-process. They do **not** read study repositories or participant transcripts. See [Getting started](../getting-started.md).
