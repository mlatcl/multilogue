---
id: "2026-10-18_cip0009-notebook-assess-subject-grain"
title: "CIP-0009: notebook Assess subject-grain section (shell + fallback)"
status: "Completed"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split"
- "2026-10-18_cip0009-ipywidgets-interaction-shell"
- "2026-10-18_cip0009-lock-artefact-multiverse-k"
tags:
- backlog
- cip0009
- notebooks
- pedagogy
- assess
---

# Task: Notebook Assess subject-grain section

> **Note**: Wires Layer B shell (or Layer A fallback) into builder notebooks.

## Description

Via `scripts/build_notebooks.py` (primary source), add an Assess section for
interactive subject grain (formats 09 and/or cluster 03):

- Prose: human grain, Bishop–Tipping dual view, Assess vs Address, **label-on-demand**
- Prefer mounting the **ipywidgets shell** when import succeeds
- Else Layer A scripted cells (merge/split by id → re-plot → optional name dirty)
- Explicit lock before Address
- Address 5e prose: multiverse holds \(k\) or \(\pm 1\) only
- Document human lock before live CIMT Address spend

Regenerate notebooks; smoke path must use non-widget / FakeClient scripted lock.

## Acceptance Criteria

- [x] Builder emits Assess subject-grain section with dual-view prose
- [x] Widget shell mounted when available; documented fallback otherwise
- [x] Address multiverse prose matches locked-\(k\) defaults
- [x] Notebooks regenerated from builder
- [x] Offline smoke / FakeClient path green without human input or widgets
- [x] Live CIMT path documents lock-before-spend

## Implementation Notes

- Do not hand-edit `.ipynb` as primary source.
- Notebook 03: dual-view shell + Layer A fallback (`MULTILOGUE_SUBJECT_GRAIN_WIDGETS=0`).
- Notebook 09: Assess lock section; Address uses locked \(k\); flowchart renumbered.
- Smoke sets `MULTILOGUE_SUBJECT_GRAIN_WIDGETS=0`.

## Related

- CIP: 0009
- REQ: 000A
- Depends on: Layer A, Layer B shell, lock artefact

## Progress Updates

### 2026-10-18

Task created (Ready) when CIP-0009 Accepted.

Updated dependencies to include Layer B ipywidgets shell after design amendment.

Implemented builder sections; regenerated notebooks; smoke 03 + 09 green.
