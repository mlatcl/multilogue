# Guide: Access

## Public loaders (in multilogue)

```python
from multilogue.access import list_sources, load

list_sources()
# ['synthetic', 'polis', 'gdn_cc', 'cdcp', 'cimt', 'decidim']

bundle = load("synthetic", n_docs_per_group=4, units_per_doc=3)
# bundle["units"], bundle["citation"], bundle["license"], bundle["path"]
```

Downloads land under `MULTILOGUE_DATAPATH` or `~/.cache/multilogue` (gitignored). Set `MULTILOGUE_ACCESS_YES=1` to skip interactive licence prompts in CI.

## Private study Access (in your package)

Your consumer owns parsers. Hand multilogue a list of unit dicts:

```python
# my_study/access.py — sketch
def load_consultation_pdfs(paths) -> list[dict]:
    units = []
    for path in paths:
        for i, chunk in enumerate(parse_pdf_to_chunks(path)):  # your code
            units.append({
                "unit_id": f"{path.stem}-{i}",
                "doc_id": path.stem,
                "text": chunk,
                "extract_text": chunk,
                "meta": {"source_path": str(path)},
            })
    return units
```

Never commit participant text into the multilogue repo. Keep study caches local and gitignored.
