# Guide: Assess

Assess helpers take units and return tables — no LLM, no research-question filters.

```python
from multilogue.access import load
from multilogue.assess_base import (
    unit_size_table, docs_per_group, empty_unit_flags, token_frequency,
)

units = load("synthetic")["units"]
sizes = unit_size_table(units)
empty = empty_unit_flags(units, min_words=4)
docs = docs_per_group(units, "group")
vocab = token_frequency(u["text"] for u in units)
```

Add study-specific plots (bibliography heuristics, OCR flags) in *your* `assess.py`. If a check only makes sense because you are studying concerns vs benefits, it belongs in Address.
