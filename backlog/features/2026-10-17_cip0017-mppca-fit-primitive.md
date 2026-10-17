---
id: "2026-10-17_cip0017-mppca-fit-primitive"
title: "CIP-0017: MPPCA topic fit primitive (k-means init, EM, responsibilities)"
status: "Completed"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0017
- mppca
- cluster
- soft
---

# Task: MPPCA topic fit primitive

> **Note**: Library work for pub-dialogue CIP-0017 / REQ-000A. Extends multilogue cluster primitives (CIP-0001).

## Description

Add a mixture-of-PPCA fit for phrase embeddings: k-means initialise component means, EM for loadings / noise / responsibilities, return soft responsibilities \(R\) (\(n \times K\)), component means \(\mu_k\), and fit metadata (including the fixed topic \(\sigma^2\) used for that run).

Default topic \(\sigma^2\) (or a short documented profile) must be explicit — CIP-0017: topic and lens floors are independent; topic \(\sigma^2\) is fixed for the analysis config, not re-fit per lens replicate.

Prefer `multilogue.cluster` or a new `multilogue.mppca` module; do not leave the only implementation in pub-dialogue.

## Acceptance Criteria

- [x] Public API fits MPPCA with k-means init and returns responsibilities, means, and topic \(\sigma^2\) used
- [x] Responsibilities are non-negative and rows sum to 1 (within tol)
- [x] Unit tests on synthetic subspace mixture: soft recover better than hard k-means under overlap
- [x] Fresh fit is deterministic given `random_state` / seed
- [x] Default topic \(\sigma^2\) documented in docstring or defaults

## Implementation Notes

- Labels are not the primary return; responsibilities are.
- May still expose MAP labels via a separate harden helper (next task).
- Coordinate with interim member-mean unify only if hard k-means path remains for other consumers.

## Related

- CIP: multilogue 0001; pub-dialogue 0017
- Consumer: `2026-10-17_cip0017-addressstage-soft-throughout` (pub-dialogue)

## Progress Updates

### 2026-10-17

Task created (Ready) when pub CIP-0017 Accepted.

Started implementation: ``multilogue.mppca.mppca_fit`` with k-means init,
fixed shared topic σ² (default 0.1), weighted PPCA EM, and tests in
``tests/test_mppca.py``. MAP helper ``responsibilities_to_labels`` included
for tests / late view (full harden-view task still open).

Implementation complete for library primitive; concept-docs task still open.
