# Soft PPCA lenses and Earth Mover's Distance

Hard *k*-means plus a single lens map assigns each cluster to one framing. Multilogue also supports a soft layer (CIP-0005 / REQ-0008). Soft-throughout topic geometry (CIP-0017) adds a **second** PPCA mixture at phrase→topic via [`multilogue.mppca`](../api/mppca.md).

## Two noise floors (CIP-0017)

| Floor | Role | Rule |
|-------|------|------|
| Topic \(\sigma^2_{\mathrm{topic}}\) | MPPCA phrase→topic fit | **Profiled once** on a short log grid (`profile_topic_sigma2`): softest σ² that still keeps separated MAP topics / means; then fixed for the run. Fallback constant: `DEFAULT_TOPIC_SIGMA2` |
| Lens \(\sigma^2_{\mathrm{lens}}\) | Soft lens mixture / σ²\* | Shared when scoring runs; chosen once by the EMD stability rule below, then fixed |

The floors are **independent**. Do not re-fit a different topic σ² per lens-mapping replicate or per document. A fixed `0.1` without profiling collapsed OpenAI embedding fits (all `q=0`, one MAP topic).

## Soft mixture weights

Each framing lens is modelled as a **probabilistic PCA** Gaussian over its member cluster centroids (shared noise σ², ARD-style factor truncation). Bayes posteriors give every cluster a mixture weight over lenses — see [`multilogue.soft.compute_mixture_weights`](../api/soft.md).

## Choosing σ² by stability

Independent LLM lens runs disagree. For each candidate σ² we recompute mixture weights per run and measure mean **Earth Mover's Distance** between runs (ground cost = cosine distance between lens means). We pick σ²* that minimises that EMD among values whose mean *effective support* lies in `(0.2, 0.6) × n_lenses`, falling back to unconstrained min-EMD if the band is empty — [`sigma2_sweep_select`](../api/soft.md).

Without the band, the minimum-EMD solution is often the near-uniform high-σ² end, where every cluster belongs almost equally to every lens and group contrasts vanish.

## Neighbour / membership rules (CIP-0006)

For sensitivity and multiverse dimensions, [`select_sigma2_one_step_harder`](../api/soft.md) / `softer` / `hard` and the named registry [`SIGMA2_RULES`](../api/soft.md) (`constrained`, `one_step_harder`, `one_step_softer`, `hard`) sit next to constrained selection. Use [`apply_sigma2_rule`](../api/soft.md) when the rule name is a string. Legacy pub rules (`min_emd`, `median`) stay in consumers.

## Soft-weighted group contrasts (CIP-0007)

Mixture weights feed document profiles and bootstrap group shares via [`soft_doc_profiles`](../api/weight.md) and [`soft_group_compare`](../api/weight.md) in `multilogue.weight`. Hard categorical [`group_compare`](../api/weight.md) is unchanged.

## Document EMD

Separately, [`multilogue.distance`](../api/distance.md) treats each document as a distribution over topics and compares documents with EMD under a cosine ground cost between topic means. Classical MDS and PERMANOVA / PERMDISP test whether groups differ in *what* they raise, without using lens names.

For **soft-throughout** consumers (CIP-0017), build those histograms with [`document_soft_topic_distributions`](../api/distance.md) (sum phrase→topic responsibilities per document). [`document_cluster_distributions`](../api/distance.md) remains the **hard-count** sensitivity / legacy path.

Install the optional extra: `pip install 'multilogue[distance]'` (pulls in POT).

Pedagogical walkthrough: [notebook 08](../notebooks.md).
