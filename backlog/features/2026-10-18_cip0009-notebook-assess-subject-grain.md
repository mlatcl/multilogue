---
id: "2026-10-18_cip0009-notebook-assess-subject-grain"
title: "CIP-0009: notebook Assess subject-grain section (viz + LLM)"
status: "Ready"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split"
- "2026-10-18_cip0009-lock-artefact-multiverse-k"
tags:
- backlog
- cip0009
- notebooks
- pedagogy
- assess
---

# Task: Notebook Assess subject-grain section

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).

## Description

Via `scripts/build_notebooks.py` (primary source), add an Assess section for
interactive subject grain (formats 09 and/or cluster 03):

- Prose: human grain, Bishop–Tipping dual view, Assess vs Address boundary
- Side-by-side **fit visualisation** and **LLM catalogue**
- Scripted merge/split demo (synthetic or cached) that refreshes both views
- Explicit lock cell (`PRIMARY_K` / lock artefact) before Address
- Address 5e prose: multiverse holds \(k\) or \(\pm 1\) only; not a wide
  resolution rewrite
- Document human lock before live CIMT Address spend

Regenerate notebooks; keep FakeClient / smoke path non-interactive (scripted
keep or default lock).

## Acceptance Criteria

- [ ] Builder emits Assess subject-grain section with viz + catalogue
- [ ] Address multiverse prose matches locked-\(k\) defaults
- [ ] Notebooks regenerated from builder
- [ ] Offline smoke / FakeClient path green without human input
- [ ] Live CIMT path documents lock-before-spend

## Implementation Notes

- Do not hand-edit `.ipynb` as primary source.
- Depends on library helpers and lock/multiverse default tasks.

## Related

- CIP: 0009
- REQ: 000A
- Depends on: `2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split`,
  `2026-10-18_cip0009-lock-artefact-multiverse-k`

## Progress Updates

### 2026-10-18

Task created (Ready) when CIP-0009 Accepted.
