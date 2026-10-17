---
id: "2026-10-17_unify-member-mean-centroids"
title: "Unify cluster centroids on normalised member means (drop sklearn cluster_centers_)"
status: "Ready"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "bugs"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0001
- cluster
- centroids
- replay
---

# Task: Unify cluster centroids on normalised member means

## Description

`multilogue.cluster` still returns sklearn `KMeans.cluster_centers_` on a fresh fit, but recomputes normalised **member means** from saved labels on freeze/replay. Those two vectors differ by ~1e-7 after L2 normalisation. Soft PPCA σ²\* selection is sensitive enough that the mismatch flips σ²\* (soft ↔ hard) under flat between-run EMD — observed in `ai-dialogue-formats` replay CI (`test_replay_reproduces_tables` / A5 weights).

This was never a deliberate dual design. The freeze-path docstring already stated member means; fresh `kmeans()` kept the sklearn convenience. Formats fixed the same split on `fix/soft-lens-replay-centroids` (PR #7). Multilogue should be the single source of truth before consumers thin further.

## Acceptance Criteria

- [ ] Fresh `kmeans` / `frozen_or_new_assignments` both expose the same centroid definition: L2-normalised mean of assigned members
- [ ] No call site in `multilogue.cluster` returns raw `cluster_centers_` as the public centroid array
- [ ] Unit test: after fit, centroids equal member means (bitwise or `allclose` at tight tol); freeze path matches fresh path for the same labels
- [ ] Docs / docstrings state the single definition (and why freeze recomputes from labels)

## Implementation Notes

- Prefer a shared helper (e.g. `_member_centroids(E, labels, k)`) used by both paths.
- Labels remain the checkpointed artefact; do not persist centroids separately unless a later CIP requires it.
- Pair with `2026-10-17_harden-sigma2-flat-emd-selection` — centroid unify fixes replay consistency; selection harden fixes the degenerate soft→hard lottery when EMD has no signal.

## Related

- CIP: 0001 (cluster primitives)
- Precedent: `ai-dialogue-formats` PR #7 / commit `8434b6a`
- Related task: `2026-10-17_harden-sigma2-flat-emd-selection`
- Consumers: `pub-dialogue`, `ai-dialogue-formats`

## Progress Updates

### 2026-10-17

Task created after diagnosing formats replay failure: fresh sklearn centres vs replay member means flipped σ²\* under identical FakeClient lens runs.
