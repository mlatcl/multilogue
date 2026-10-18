# Shared topic space

After extraction, phrases live in one embedding space. Legacy consumers partition with hard *k*-means. Soft-throughout consumers (CIP-0017) fit a **mixture of PPCA** ([`multilogue.mppca.mppca_fit`](../api/mppca.md)): *k*-means only initialises component means; soft responsibilities are the primary topic state. Harden to MAP labels / exemplars only at LLM or report boundaries (`responsibilities_to_labels`, `example_phrases_for_soft_topics`). Exemplars for a topic are phrases with responsibility at least `1/k` by default (override with `min_responsibility`), capped at `n_top` — not a fixed pad of 12.

## Frozen assignments

*k*-means is sensitive to initialisation and is not bit-stable across machines. When the set of `phrase_id`s is unchanged, [`frozen_or_new_assignments`](../api/cluster.md) reloads saved labels so later notebooks do not silently reshuffle topics. Soft MPPCA consumers should likewise checkpoint responsibilities (or fit params + data hash) for replay.

## Blind labels and lenses

Cluster **labels** and framing **lenses** are proposed from example phrases alone — without group columns (format, technology, …) in the prompt. Researchers may edit the lens map afterwards; the first pass stays format-blind.

## PCA diagnostics vs PPCA

Notebook and `multilogue.viz.embedding_scatter` plots use **classical PCA** as a viewing device (directions of high variance). That is not a claim that phrases were generated from probabilistic PCA. Soft PPCA lens memberships, σ² selection by EMD, and document-level EMD live in [`multilogue.soft`](../api/soft.md) and [`multilogue.distance`](../api/distance.md) — see [Soft PPCA and EMD](soft-ppca-emd.md).
