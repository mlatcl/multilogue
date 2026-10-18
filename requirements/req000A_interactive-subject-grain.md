---
id: "000A"
title: "Analysts can interactively set subject grain before Address locks topics"
status: "Implemented"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
related_tenets:
- "assess-without-the-question"
- "shared-methodology-not-study-logic"
stakeholders:
- "multilogue maintainers"
- "formats and pub-dialogue notebook users"
tags:
- "assess"
- "eda"
- "topics"
- "visualisation"
- "human-in-the-loop"
---

# REQ-000A: Analysts can interactively set subject grain before Address locks topics

## Description

After phrases are embedded, analysts can explore soft topic structure as
**question-agnostic EDA** with a **dual view**: (1) latent / mixture
**visualisation of the current fit** (Bishop–Tipping channel — geometry updates
as models are fit, merged, and split), and (2) **LLM catalogues** of the same
bags (exemplars + blind names). Analysts merge or split topics until the subject
list is human-defensible. That exploration does not maximise a study metric
(e.g. format-gap \(\ell\)).

Only after the analyst **locks** a subject catalogue does Address proceed
(lenses, group contrasts, multiverse). Multiverse sensitivity then holds that
grain or varies it only locally (\(\pm 1\)), rather than treating a wide \(k\)
grid as a peer of quote / kind / membership choices.

**Why this matters**: Topic count \(k\) defines how many subjects the analysis
admits. Putting a wide \(k\) grid in a factorial multiverse swamps other
analytic choices and answers the wrong question. Subject grain is a human
resolution decision; machine diagnostics only screen usable partitions. Phrase
topics need both geometry (nesting / separability) and wording (what the bag
is about).

**Who benefits**: Anyone running formats-style or soft-throughout pipelines who
needs a defensible topic catalogue before claiming stability of \(\ell\).

## Acceptance Criteria

- [x] Analysts can view a **latent visualisation of the current soft fit**
      (updating after fit / merge / split) without committing to a research-question
      metric
- [x] Analysts can view a soft-topic **LLM catalogue** (exemplars + summary) for
      the same bags
- [x] Analysts can request **merge** and **split** of topics and see updated
      geometry immediately; LLM catalogues refresh for affected bags without
      requiring a full re-run of Address
- [x] Live exploration supports undo and an explicit lock action (notebook shell
      or equivalent); labelling of changed topics is on demand, not forced on
      every structural click
- [x] A locked subject grain is an explicit artefact handed to Address
- [x] Formats (or equivalent) multiverse does not let a wide \(k\) grid dominate
      variance shares by default
- [x] Offline / FakeClient path remains usable for pedagogy and CI without widgets

## Notes

LLM topic names are reading aids over exemplars (format-blind harden view), not
ground truth and not an automatic selector of \(k\). Fit visualisation is
required alongside catalogues. Live try-combinations UX is an **ipywidgets**
notebook shell (merge/split/undo/lock) with **label-on-demand** for dirty
topics — not auto-LLM on every click, and not click-on-canvas in v1. A
scripted non-widget path must remain for CI / FakeClient.

## References

- **Related Tenets**: assess-without-the-question, shared-methodology-not-study-logic
- **External**: Bishop & Tipping (1998), *A Hierarchical Latent Variable Model
  for Data Visualization*, IEEE TPAMI 20(3):281–293

## Progress Updates

### 2026-10-18
Requirement drafted with CIP-0009 (Proposed). Clarified: Bishop–Tipping **fit
visualisation** and LLM merge/split catalogues are both required Assess views.

CIP-0009 Accepted → In Progress; backlog tasks Ready (lock/multiverse, library
viz+merge/split, notebook Assess section).

CIP-0009 amended: Interaction shell (ipywidgets Layer B, label-on-demand, undo);
backlog split Layer A vs Layer B.

CIP-0009 Implemented: Layer A/B + lock + notebooks 03/09; awaiting PR / close.
