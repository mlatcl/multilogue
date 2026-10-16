# Guide: Address pipeline

Typical Address flow on units you already assessed:

```python
from pathlib import Path
import numpy as np
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table, yield_report
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, frozen_or_new_assignments, example_phrases_for_clusters,
    make_label_work, make_lens_work, resolve_lenses,
)
from multilogue.weight import group_compare
from multilogue.multiverse import enumerate_configurations, run_multiverse, variance_decomposition

# units: list[dict] from your Access
units_by_id = {u["unit_id"]: u for u in units}
client = FakeClient()  # or OpenAIClient / LiteLLMClient
root = Path("outputs/run")
runner = StageRunner(root / "ckpt", root / "logs", sleep=lambda _: None)

extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client, kind=kind, system=YOUR_SYSTEM,  # study prompt
        user_for_unit=lambda u: u["text"], model="…",
        sentinel=f"NO_{kind.upper()}", quote_threshold=0.8,
    )
    extraction[kind] = runner.run(
        f"extract_{kind}", units, lambda u: u["unit_id"], work,
        f"extract|{kind}|v1", quiet=True,
    )

phrases = phrase_table(
    extraction, units_by_id, kinds=["concern", "benefit"],
    extra_unit_fields=["group"],  # or format / technology
)

k = 6
E = np.asarray(Embedder(root / "emb", client, "emb-model")(phrases.phrase.tolist()), float)
labels, centroids, frozen = frozen_or_new_assignments(phrases, E, k, 0, root / "clusters")
phrases = phrases.assign(
    cluster=labels,
    centroid_sim=(E * centroids[labels]).sum(1),
)

# blind labels → lenses → document-weighted compare → your ℓ multiverse
# (see cookbooks for package layout)
```

Replace `FakeClient` and `YOUR_SYSTEM` in real studies. Keep paper-specific ℓ inside your package's callback.
