---
id: "2026-10-18_assess-uq-hover-paragraphs"
title: "Hover paragraph text on Assess local U_q points"
status: "Proposed"
priority: "Medium"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009", "000A"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- assess
- viz
- plotly
- subject-grain
---

# Task: Hover paragraphs on Assess \(U_q\) points

## Description

In the Assess subject-grain dual view, hovering a point should show the
underlying phrase / paragraph text (not just geometry). Static matplotlib
figures cannot do this well in the notebook widget path.

Add an interactive hover layer for local \(U_q\), proposed-split, and
proposed-merge views used by `SubjectGrainShell`, while keeping matplotlib for
saved PNG artefacts and non-notebook report paths.

## Acceptance Criteria

- [ ] Hovering a point in the Assess shell shows the phrase (and truncated
      paragraph / unit text when available)
- [ ] Covers `topic_fit_view`, proposed-split, and proposed-merge panels in
      the widget path
- [ ] Matplotlib save/export path unchanged (no Plotly required for CI / report
      figures)
- [ ] Plotly (or chosen stack) is an optional notebook extra, not a hard core
      dependency
- [ ] Smoke test or thin unit coverage for hover-payload construction (text
      aligned to point indices)

## Implementation Notes

- Current stack: `multilogue/viz.py` + matplotlib; `notebook` extra is
  ipywidgets + matplotlib only — no Plotly yet.
- Prefer Plotly for Jupyter hover; pass `phrases` / optional longer text column
  through `SubjectGrainShell.fit_view` → viz helpers.
- Keep Bishop–Tipping semantics: project all points into the focus component’s
  plane; ink/opacity still ∝ soft mass; hover text is a reading aid, not a
  harden view.
- Truncate long paragraphs in the tooltip; full text can stay in the catalogue
  table.
- No new CIP unless the dependency / dual-backend design needs a longer HOW;
  this task extends CIP-0009 Assess UX (with CIP-000A grain-shell context).

## Related

- CIP: 0009 (interactive subject grain / dual view)
- CIP: 000A (Assess grain shell defaults)
- Code: `multilogue/viz.py`, `multilogue/subject_grain_shell.py`

## Progress Updates

### 2026-10-18

Task created (Proposed) after fixed-\(\sigma^2\) Assess entry validated in
notebook 03.
