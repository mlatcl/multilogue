---
id: "000A"
title: "Analysts can interactively set subject grain before Address locks topics"
status: "Proposed"
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

- [ ] Analysts can view a **latent visualisation of the current soft fit**
      (updating after fit / merge / split) without committing to a research-question
      metric
- [ ] Analysts can view a soft-topic **LLM catalogue** (exemplars + summary) for
      the same bags
- [ ] Analysts can request **merge** and **split** of topics and see **both**
      updated geometry and catalogues for parent / children (or merged bag)
- [ ] A locked subject grain is an explicit artefact handed to Address
- [ ] Formats (or equivalent) multiverse does not let a wide \(k\) grid dominate
      variance shares by default
- [ ] Offline / FakeClient path remains usable for pedagogy and CI

## Notes

LLM topic names are reading aids over exemplars (format-blind harden view), not
ground truth and not an automatic selector of \(k\). Fit visualisation is
required alongside catalogues; a full click-on-canvas GUI is not required if
notebook-driven merge/split still re-draws the Bishop–Tipping-style view.

## References

- **Related Tenets**: assess-without-the-question, shared-methodology-not-study-logic
- **External**: Bishop & Tipping (1998), *A Hierarchical Latent Variable Model
  for Data Visualization*, IEEE TPAMI 20(3):281–293

## Progress Updates

### 2026-10-18
Requirement drafted with CIP-0009 (Proposed). Clarified: Bishop–Tipping **fit
visualisation** and LLM merge/split catalogues are both required Assess views.
