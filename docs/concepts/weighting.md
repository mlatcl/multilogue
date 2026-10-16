# Document weighting

If every phrase counts equally, a long document dominates the comparison. Multilogue averages **within documents first**, then across documents.

## Shares and bootstrap

[`doc_profile`](../api/weight.md) builds per-document shares of a categorical column (cluster or lens). [`group_compare`](../api/weight.md) reports group-level percentages with a **cluster bootstrap** that resamples documents (not phrases).

## Binary presence

[`doc_binary_presence`](../api/weight.md) asks whether a document raised a cluster at all — useful for temporal or rarity views.

## What stays in the study

Distances between whole topic profiles (earth-mover style comparisons, PERMANOVA, …) consume these shares but are not implemented here. Keep them in the consumer package.
