---
id: "0008"
title: "Soft PPCA lens memberships with σ² selected by EMD stability"
status: "Implemented"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
related_tenets:
- "shared-methodology-not-study-logic"
- "reproducibility-via-fingerprints"
stakeholders:
- "theme-structure analyses"
- "pub-dialogue consumer"
tags:
- "clustering"
- "ppca"
- "emd"
- "address"
---

# REQ-0008: Soft PPCA lens memberships with σ² selected by EMD stability

## Description

Studies that group clusters into framing lenses can obtain **soft mixture weights** over lenses for each cluster, using a shared-noise PPCA likelihood, and can choose the noise scale σ² by measuring **stability across independent lens runs** with Earth Mover's Distance. Document-level topic profiles can be compared with EMD under a cosine ground cost between cluster centroids, with optional MDS and PERMANOVA / PERMDISP for group tests.

**Why this matters**: Hard lens assignment and classical PCA-as-view omit the generative soft-membership story and the principled σ² choice that `pub-dialogue` already uses for shared-structure, robustness, multiverse, and document-distance analyses. That methodology belongs in the shared library so a second consumer does not reimplement it.

**Who benefits**: Any study that wants soft affinity to framing lenses and transport-based distances between document topic mixtures.

## Acceptance Criteria

- [x] Callers can compute per-cluster mixture weights over lenses from centroids, a lens→cluster mapping, and σ²
- [x] Callers can sweep σ² and select a stability-optimal value using mean EMD across N independent lens-run mappings, with an effective-support constraint
- [x] Callers can build document×cluster distributions and pairwise EMD under cosine ground cost; optional MDS and PERMANOVA / PERMDISP return structured results
- [x] Tests use synthetic centroids and mappings only; POT (or equivalent) is an optional dependency, not required for core install
- [x] Docs and notebooks explain PPCA soft memberships and EMD as first-class method, not as consumer-only Address

## Notes

Hard k-means clustering and blind multi-run lens *generation* remain under REQ-0003. This requirement covers the soft layer and transport distances that consume those artefacts.

Document EMD answers “do groups differ in *what* they raise?” without using LLM lens names. Soft PPCA answers “how softly does each cluster sit under each framing lens?” — related but distinct uses of EMD (run-to-run mixture stability vs document-to-document profile distance).

## References

- **Related Tenets**: shared-methodology-not-study-logic; reproducibility-via-fingerprints
- **Source implementation**: `pub_dialogue.address` (`fit_lens_ppca`, `compute_mixture_weights`, `sigma2_sweep_select`, `pairwise_mean_emd`); `pub_dialogue.distance`

## Progress Updates

### 2026-10-16
Requirement created at Ready status after confirming the material lives in `pub-dialogue` and was excluded from multilogue by CIP-0001's original boundary.

### 2026-10-16 (later)
Implemented via CIP-0005: `multilogue.soft`, `multilogue.distance`, notebook 08, optional `distance` extra.
