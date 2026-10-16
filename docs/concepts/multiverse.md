# Multiverse

Following Bell, Kampman, Dodge & Lawrence (2022), multilogue enumerates a Cartesian product of analytic choices and asks a **consumer-supplied** callback for the headline metric ℓ under each configuration.

```python
from multilogue.multiverse import (
    enumerate_configurations, run_multiverse, variance_decomposition,
)

dims = {"k": [4, 5, 6], "threshold": [0.4, 0.5]}
configs = enumerate_configurations(dims)

def evaluate(cfg):
    # Your paper metric — formats gap, technology distinctiveness, …
    return {"ell": 0.5 + 0.1 * cfg["k"]}

results = run_multiverse(configs, evaluate)
shares = variance_decomposition(results, "ell", list(dims))
```

One-way variance shares are a first-cut diagnostic: interactions mean shares need not sum to one. The library must not hard-code paper outcomes.
