---
id: "2026-10-16_cip0006-thin-consumers-sigma2"
title: "Thin pub + formats onto multilogue σ² neighbour rules"
status: "Completed"
priority: "Medium"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0006"]
owner: "Neil Lawrence"
dependencies: ["2026-10-16_cip0006-sigma2-neighbour-rules"]
tags:
- backlog
- cip0006
- consumer
---

# Task: Thin pub + formats onto multilogue σ² neighbour rules

## Description

After CIP-0006 core lands: remove duplicate neighbour implementations from pub `multiverse` and wire formats `rule_sigma2` to `apply_sigma2_rule` / display-label map.

## Acceptance Criteria

- [x] Pub imports `SIGMA2_RULES` + neighbour selectors from `multilogue.soft`
- [x] `LEGACY_SIGMA2_RULES` remain in pub only
- [x] Formats `rule_sigma2` uses multilogue for non-hard rules when `n_lenses` given
- [x] `tests/test_multiverse_sigma2.py` still green

## Related

- CIP: 0006

## Progress Updates

### 2026-10-16

Thin-out applied on consumer `cip0005-depend-multilogue` branches.
