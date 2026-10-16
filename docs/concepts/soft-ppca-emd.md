# Soft PPCA lenses and Earth Mover's Distance

Hard *k*-means plus a single lens map assigns each cluster to one framing. Multilogue also supports a soft layer (CIP-0005 / REQ-0008).

## Soft mixture weights

Each framing lens is modelled as a **probabilistic PCA** Gaussian over its member cluster centroids (shared noise σ², ARD-style factor truncation). Bayes posteriors give every cluster a mixture weight over lenses — see [`multilogue.soft.compute_mixture_weights`](../api/soft.md).

## Choosing σ² by stability

Independent LLM lens runs disagree. For each candidate σ² we recompute mixture weights per run and measure mean **Earth Mover's Distance** between runs (ground cost = cosine distance between lens means). We pick σ²* that minimises that EMD among values whose mean *effective support* lies in `(0.2, 0.6) × n_lenses`, falling back to unconstrained min-EMD if the band is empty — [`sigma2_sweep_select`](../api/soft.md).

Without the band, the minimum-EMD solution is often the near-uniform high-σ² end, where every cluster belongs almost equally to every lens and group contrasts vanish.

## Document EMD

Separately, [`multilogue.distance`](../api/distance.md) treats each document as a distribution over clusters and compares documents with EMD under a cosine ground cost between centroids. Classical MDS and PERMANOVA / PERMDISP test whether groups differ in *what* they raise, without using lens names.

Install the optional extra: `pip install 'multilogue[distance]'` (pulls in POT).

Pedagogical walkthrough: [notebook 08](../notebooks.md).
