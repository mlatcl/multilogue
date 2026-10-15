---
id: "document-level-weighting"
title: "Document-Level Weighting"
status: "Active"
created: "2026-10-15"
last_reviewed: "2026-10-15"
review_frequency: "Annual"
conflicts_with: []
tags:
- tenet
- statistics
---

# Project Tenet: Document-Level Weighting

## Description

Long transcripts and verbose reports must not dominate theme shares. Multilogue averages over documents (conversations, dialogue reports), not over pooled points, and uses document resampling for uncertainty. Temporal presence uses document-level binary weighting: the fraction of documents in a period that raise a theme, not raw phrase counts.

## Quote

*"Count documents; do not let the longest voice win."*

## Examples

- Per-document share profiles then mean across documents
- Cluster bootstrap that resamples document ids
- Yearly charts as fraction of documents mentioning a cluster

## Counter-examples

- Pooling all phrases then computing percentages
- Letting a single long workshop set the theme mix
- Plotting raw phrase counts over years without document normalisation

## Conflicts

- Point-level phenomena (e.g. story sequences within a transcript)
- Resolution: use point-level measures where the unit of interest is the turn; report document-weighted shares for corpus-level claims
