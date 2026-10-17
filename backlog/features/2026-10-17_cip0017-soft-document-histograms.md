---
id: "2026-10-17_cip0017-soft-document-histograms"
title: "CIP-0017: soft document topic histograms for EMD"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0005"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-mppca-fit-primitive"
tags:
- backlog
- cip0017
- emd
- distance
- soft
---

# Task: Soft document topic histograms

## Description

Extend `multilogue.distance` so document→topic distributions can be built by **summing soft responsibilities** per document (rows of \(R\) aggregated by doc), not only hard cluster counts. Cosine ground cost continues to use component means \(\mu\). Keep a named hard-count path as an explicit sensitivity view.

## Acceptance Criteria

- [ ] API accepts soft mass (phrases × topics + doc ids) and returns row-stochastic \(P\)
- [ ] Hard-count path remains available under a clear name / flag
- [ ] Existing EMD / MDS tests still pass; new soft-histogram tests added
- [ ] Docs note soft as the CIP-0017 default for consumers that adopt soft-throughout

## Implementation Notes

min_phrases (or min soft mass) threshold policy: document in API — prefer total responsibility mass ≥ threshold analogous to today's min phrase count.

## Related

- CIP: multilogue 0005; pub-dialogue 0017
- Consumer: `2026-10-17_cip0017-wire-soft-lenses-and-emd`

## Progress Updates

### 2026-10-17

Task created (Ready).
