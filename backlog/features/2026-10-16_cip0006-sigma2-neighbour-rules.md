---
id: "2026-10-16_cip0006-sigma2-neighbour-rules"
title: "Implement σ² neighbour rules + SIGMA2_RULES in multilogue.soft"
status: "Completed"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0006"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0006
- soft
- sigma2
---

# Task: Implement σ² neighbour rules + SIGMA2_RULES in multilogue.soft

## Description

Port pub-dialogue neighbour helpers (`select_sigma2_one_step_harder|softer|hard`) and the named `SIGMA2_RULES` registry into `multilogue.soft`, with pytest coverage matching the existing multiverse σ² fixtures.

## Acceptance Criteria

- [x] Neighbour helpers + `SIGMA2_RULES` + `apply_sigma2_rule` in `multilogue.soft`
- [x] Tests in `tests/test_soft.py` for harder/softer/hard/unknown rule
- [x] Pub `multiverse` re-exports from multilogue (legacy rules stay local)
- [x] Formats `rule_sigma2` adapts display labels onto the registry (hard → None local)

## Implementation Notes

Behaviour matches pub: neighbours of **constrained** σ²\* on the swept grid, clipped. Formats `hard` remains `None` for true one-hot via `weights_for`.

## Related

- CIP: 0006
- Consumers: `pub_dialogue/multiverse.py`, `dialogue_formats/soft_lenses.py`

## Progress Updates

### 2026-10-16

CIP Accepted; implementation complete in `soft.py` + consumer thin-out; pytest green.
