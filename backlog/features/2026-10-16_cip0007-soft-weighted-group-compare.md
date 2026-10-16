---
id: "2026-10-16_cip0007-soft-weighted-group-compare"
title: "Implement soft_doc_profiles + soft_group_compare in multilogue.weight"
status: "Completed"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0007"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0007
- soft
- weight
---

# Task: Implement soft_doc_profiles + soft_group_compare in multilogue.weight

## Description

Add generic soft-weighted document profiles and two-group bootstrap contrasts to `multilogue.weight`, then thin formats `soft_compare` / `_doc_profiles` onto them. Study-specific column renames stay in consumers.

## Acceptance Criteria

- [x] `soft_doc_profiles` and `soft_group_compare` in `multilogue.weight`
- [x] Synthetic pytest (profiles sum ~1; planted group gap)
- [x] Formats `soft_compare` wraps soft_group_compare with chatbot/workshop column names
- [x] Hard `group_compare` unchanged

## Implementation Notes

API mirrors formats soft path but takes a generic `group_col` / `groups` list. Pub soft R2 tech-salience helpers that need technology columns stay local for now.

## Related

- CIP: 0007
- Consumers: `dialogue_formats/soft_lenses.py`

## Progress Updates

### 2026-10-16

CIP Accepted; implementation complete in `weight.py` + formats thin-out; pytest green.
