---
id: "0003"
title: "Phrases share one embedding space with frozen clusters and lenses"
status: "Implemented"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
related_tenets:
- "shared-methodology-not-study-logic"
- "reproducibility-via-fingerprints"
stakeholders:
- "theme-structure analyses"
- "format-comparison analyses"
tags:
- "clustering"
- "address"
---

# REQ-0003: Phrases share one embedding space with frozen clusters and lenses

## Description

Extracted phrases can be embedded, clustered with k-means, labelled without the grouping variable in the prompt, and grouped into framing lenses. Cluster assignments freeze when the phrase set is unchanged so labels remain stable across machines.

**Why this matters**: Both consumer papers need a shared topic space; freezing assignments protects reproducibility.

**Who benefits**: Any study comparing groups within one theme space.

## Acceptance Criteria

- [ ] Embedder caches vectors by phrase hash
- [ ] Frozen assignment load/save when phrase ids match
- [ ] Blind labelling and multi-run lens grouping APIs accept consumer-supplied prompts via the client
- [ ] Tests use FakeClient / synthetic embeddings; no live API

## Progress Updates

### 2026-10-15
Requirement created at Ready status from the multilogue package plan.
