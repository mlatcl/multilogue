---
id: "2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split"
title: "CIP-0009: Layer A topic fit viz, catalogue, merge/split (no UI)"
status: "Completed"
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

# Task: Layer A — topic fit viz + catalogue + merge/split

> **Note**: Pure model/viz APIs. No ipywidgets in this task (that is Layer B).

## Description

Implement Assess-owned **Layer A** helpers for the Bishop–Tipping dual view:

1. **Fit visualisation** — 2-D latent / mixture view of the current soft fit
   (points, soft membership cues, component means; parent/child panels after
   split). Recomputable after fit / merge / split.
2. **Topic catalogue** — table of exemplars (+ optional label fields + dirty
   flag column) for the same bags.
3. **`propose_merge` / `propose_split`** — update soft state; return dirty topic
   ids for later labelling (do **not** call the LLM here).

Machine-screen diagnostics (collapse, tiny mass, mean max-\(r\), entropy) may
be surfaced alongside; they do not auto-choose grain.

## Acceptance Criteria

- [x] Viz helper produces finite 2-D coords and responsibility-aware colouring
- [x] Catalogue helper is deterministic given seed / exemplars
- [x] Merge and split update responsibilities (or equivalent) without raising on
      synthetic planted mixtures; return dirty ids
- [x] Unit tests cover viz finiteness, catalogue stability, merge-then-split
      recovery of separable structure
- [x] No `ipywidgets` import; no dependence on format-gap \(\ell\)

## Implementation Notes

- `multilogue/subject_grain.py`: `propose_merge`, `propose_split`,
  `topic_catalogue`, diagnostics.
- `multilogue.viz.topic_fit_view` for the Bishop–Tipping channel.
- LLM calls stay at StageRunner / Layer B edge only.
- Follow-on: `2026-10-18_cip0009-ipywidgets-interaction-shell`.

## Related

- CIP: 0009
- REQ: 000A
- Follow-on: Layer B widget shell; notebook Assess section

## Progress Updates

### 2026-10-18

Task created (Ready) when CIP-0009 Accepted.

Clarified as **Layer A only** after interaction-shell design amendment
(widgets moved to separate backlog task).

Implemented Layer A + tests (`tests/test_subject_grain.py`).
