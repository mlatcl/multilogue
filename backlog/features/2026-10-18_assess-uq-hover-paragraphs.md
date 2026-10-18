---
id: "2026-10-18_assess-uq-hover-paragraphs"
title: "Hover paragraph text on Assess local U_q points"
status: "Completed"
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

- [x] Hovering a point in the Assess shell shows the phrase (and truncated
      paragraph / unit text when available)
- [x] Covers `topic_fit_view`, proposed-split, and proposed-merge panels in
      the widget path
- [x] Matplotlib save/export path unchanged (no Plotly required for CI / report
      figures)
- [x] Plotly (or chosen stack) is an optional notebook extra, not a hard core
      dependency
- [x] Smoke test or thin unit coverage for hover-payload construction (text
      aligned to point indices)

## Implementation Notes

- `hover_phrase_texts` / `_plotly_uq_figure` in `multilogue/viz.py`
- Shell `hover_texts()` prefers paragraph/text columns when present
- Widget `fig_out` displays Plotly when available; falls back to matplotlib
- `path=` always forces matplotlib PNG export

## Related

- CIP: 0009 (interactive subject grain / dual view)
- CIP: 000A (Assess grain shell defaults)
- Code: `multilogue/viz.py`, `multilogue/subject_grain_shell.py`

## Progress Updates

### 2026-10-18

Task created (Proposed) after fixed-\(\sigma^2\) Assess entry validated in
notebook 03.

### 2026-10-18

Implemented Plotly hover path; backlog Completed.

### 2026-10-18

UX tweak: smaller markers; click fills a side HTML readout; split children
ordered by soft mass (largest first / default selection).
