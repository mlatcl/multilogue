---
id: "2026-10-17_cip0017-harden-view-helpers"
title: "CIP-0017: harden-view helpers (MAP labels, exemplars for LLM I/O)"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-mppca-fit-primitive"
tags:
- backlog
- cip0017
- harden
- llm
- soft
---

# Task: Harden-view helpers

## Description

Provide deterministic helpers that turn soft responsibilities into discrete views for LLM labelling / lens-partition prompts and human tables: MAP `cluster_id`, top-mass exemplar phrase selection per component, optional thresholded multi-label view if needed later.

Hardening is a **view**, not a stored primary state.

## Acceptance Criteria

- [x] `responsibilities_to_labels` (or equivalent) = row-wise argmax; documented
- [x] Exemplar selection given phrases + \(R\) is deterministic under a seed
- [x] Unit tests: MAP matches `argmax`; empty/degenerate rows handled
- [x] Docstring states these are for LLM/report boundaries only

## Implementation Notes

pub-dialogue `label_cluster` / framing-lens cells should call these rather than assuming hard k-means assignments exist upstream.

## Related

- CIP: pub-dialogue 0017
- Depends: `2026-10-17_cip0017-mppca-fit-primitive`

## Progress Updates

### 2026-10-17

Task created (Ready).

### 2026-10-17 (impl)

Completed in ``multilogue.mppca`` + ``tests/test_mppca_harden.py``.
