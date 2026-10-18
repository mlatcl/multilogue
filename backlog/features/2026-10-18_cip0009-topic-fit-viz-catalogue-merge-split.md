---
id: "2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split"
title: "CIP-0009: topic fit visualisation, catalogue, merge/split helpers"
status: "Ready"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0009
- assess
- mppca
- visualisation
- eda
---

# Task: Topic fit viz + catalogue + merge/split

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).

## Description

Implement Assess-owned library helpers for the Bishop–Tipping dual view:

1. **Fit visualisation** — 2-D latent / mixture view of the current soft fit
   (points, soft membership cues, component means; parent/child panels after
   split). Recomputable after fit / merge / split.
2. **Topic catalogue** — table of exemplars (+ optional LLM label fields) for
   the same bags.
3. **`propose_merge` / `propose_split`** — update soft state for discrete human
   actions; return bags to re-plot and re-label.

Machine-screen diagnostics (collapse, tiny mass, mean max-\(r\), entropy) may
be surfaced alongside; they do not auto-choose grain.

## Acceptance Criteria

- [ ] Viz helper produces finite 2-D coords and responsibility-aware colouring
- [ ] Catalogue helper is deterministic given seed / exemplars
- [ ] Merge and split update responsibilities (or equivalent) without raising on
      synthetic planted mixtures
- [ ] Unit tests cover viz finiteness, catalogue stability, merge-then-split
      recovery of separable structure
- [ ] No dependence on format-gap \(\ell\) or other Address metrics

## Implementation Notes

- Prefer additives on `viz` / `mppca` / thin `assess` module; Assess ownership
  of the *loop* matters more than file name.
- v1 is API + matplotlib figures, not a click-canvas GUI.
- Reuse existing exemplar / label plumbing where possible; LLM calls stay at
  the notebook/StageRunner edge.

## Related

- CIP: 0009
- REQ: 000A
- Follow-on: notebook Assess section task

## Progress Updates

### 2026-10-18

Task created (Ready) when CIP-0009 Accepted.
