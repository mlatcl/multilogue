---
id: "2026-10-16_cip0005-finish-pub-soft-distance-adopt"
title: "Finish / merge CIP-0005 soft+distance adopt in pub-dialogue"
status: "In Progress"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0005"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0005
- consumer
- pub-dialogue
---

# Task: Finish / merge CIP-0005 soft+distance adopt in pub-dialogue

## Description

CIP-0005 follow-on (explicitly listed in CIP implementation status): land `cip0005-depend-multilogue` so pub-dialogue thin-wraps `multilogue.soft` and `multilogue.distance` (`source_file` / `cluster_id` defaults), and `AddressStage.sigma2_sweep_select` / multiverse constrained selection delegate to multilogue.

## Acceptance Criteria

- [ ] `pyproject.toml` depends on `multilogue[distance]` with hatch `allow-direct-references`
- [ ] `distance.py` is thin wrapper; `address` PPCA helpers + sweep delegate to multilogue
- [ ] Multiverse imports `CANONICAL_SUPPORT_BAND`, `select_sigma2_constrained` / `in_band`, `mean_n_lenses` from multilogue
- [ ] `tests/test_distance.py` and `tests/test_multiverse_sigma2.py` pass
- [ ] Branch reviewed and merged (or ready for PR)

## Implementation Notes

Parity vs `main` (2026-10-16): exact match on mixture, σ²\*, EMD matrix, MDS, PERMANOVA. Neighbour σ² rules (`one_step_*`) remain local until CIP-0006.

## Related

- CIP: 0005
- Branch: `cip0005-depend-multilogue` on mlatcl/pub-dialogue
- Related: `2026-10-15_cip0001-thin-pub-dialogue`

## Progress Updates

### 2026-10-16

Task created. Soft/distance thin-out implemented on branch; tests + parity green.
