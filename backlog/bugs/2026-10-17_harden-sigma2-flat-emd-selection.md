---
id: "2026-10-17_harden-sigma2-flat-emd-selection"
title: "Harden σ²* selection when between-run EMD is flat / near-hard is in-band"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "bugs"
related_cips: ["0005", "0006"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0005
- cip0006
- soft
- sigma2
- emd
---

# Task: Harden σ²* selection under flat EMD

## Description

`select_sigma2_in_band` / `sigma2_sweep_select` pick min mean EMD among σ² with effective support in `(0.2, 0.6) × n_lenses`. For two lenses that band is `(0.4, 1.2)`, so **fully hard** assignment (eff support = 1.0) is allowed. When lens runs are identical (or nearly so), between-run EMD is ~0 for every σ² and the argmin is a float lottery — tiny centroid or solver noise can switch σ²\* from mildly soft (~0.1) to hard (~1e-4).

CIP-0005 preserved the pub-dialogue rule without a degeneracy guard. Formats smoke tests with identical FakeClient lens runs exposed the failure mode. Centroid unify (separate task) removes one source of fresh/replay flip; the library should still refuse a meaningless “stability” pick when EMD has no signal.

## Acceptance Criteria

- [ ] Documented behaviour when EMD spread in-band is below a small threshold (or when all mappings are identical): deterministic tie-break and/or exclude near-hard from the “soft” band
- [ ] `select_sigma2_in_band` / `sigma2_sweep_select` implement that behaviour; warn or flag in returned info when selection is degenerate
- [ ] Tests: identical lens mappings → stable σ²\* across tiny centroid perturbations; hard (eff≈1) is not selected as a “soft” star when a non-degenerate rule applies
- [ ] Concept doc (`docs/concepts/soft-ppca-emd.md`) notes the degeneracy case and the rule change (multiverse sensitivity note if behaviour changes vs historical unconstrained min-EMD-in-band)

## Implementation Notes

Candidate approaches (pick one; record choice in CIP note or this task):

1. **Exclude near-hard** — tighten band lower bound so eff support must exceed ~1 + ε (or use a floor above 1.0 for n_lenses ≥ 2).
2. **Flat-EMD tie-break** — if `max(EMD) − min(EMD)` in-band < ε, pick a canonical rule (e.g. largest in-band σ², or mid-band) rather than `idxmin` noise.
3. **Identical mappings short-circuit** — if all run mappings are equal, skip EMD “stability” and apply an explicit default (document clearly).

Do not invent a new scientific rule without noting impact on existing multiverse / paper sensitivity language (CIP-0005: “Do not invent a new rule without a multiverse sensitivity note”).

## Related

- CIP: 0005 (soft PPCA / EMD), 0006 (σ² neighbour rules)
- Related task: `2026-10-17_unify-member-mean-centroids`
- Consumers: `pub_dialogue.address` / `multiverse`, `dialogue_formats.soft_lenses`
- Symptom: formats CI soft→hard on A5 weights when FakeClient lens runs are identical

## Progress Updates

### 2026-10-17

Task created. Diagnosis: FakeClient identical even/odd lens runs ⇒ EMD≈0 for all σ²; band includes hard; sklearn vs member-mean centroids tipped different winners.
