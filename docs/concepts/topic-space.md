# Shared topic space

After extraction, phrases live in one embedding space and are partitioned with *k*-means.

## Frozen assignments

*k*-means is sensitive to initialisation and is not bit-stable across machines. When the set of `phrase_id`s is unchanged, [`frozen_or_new_assignments`](../api/cluster.md) reloads saved labels so later notebooks do not silently reshuffle topics.

## Blind labels and lenses

Cluster **labels** and framing **lenses** are proposed from example phrases alone — without group columns (format, technology, …) in the prompt. Researchers may edit the lens map afterwards; the first pass stays format-blind.

## PCA diagnostics vs PPCA

Notebook and `multilogue.viz.embedding_scatter` plots use **classical PCA** as a viewing device (directions of high variance). That is not a claim that phrases were generated from probabilistic PCA. Soft PPCA lens memberships and σ² sweeps are study-specific Address work and stay out of multilogue.
