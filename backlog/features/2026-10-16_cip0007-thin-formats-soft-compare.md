---
id: "2026-10-16_cip0007-thin-formats-soft-compare"
title: "Thin formats soft_compare onto multilogue.weight soft helpers"
status: "Completed"
priority: "Medium"
created: "2026-10-16"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0007"]
owner: "Neil Lawrence"
dependencies: ["2026-10-16_cip0007-soft-weighted-group-compare"]
tags:
- backlog
- cip0007
- consumer
- ai-dialogue-formats
---

# Task: Thin formats soft_compare onto multilogue.weight soft helpers

## Description

Replace local `_doc_profiles` / bootstrap loop in formats `soft_compare` with `soft_doc_profiles` / `soft_group_compare`, keeping formats column names (`difference_w_minus_c`, `chat_lo`, …).

## Acceptance Criteria

- [x] `_doc_profiles` delegates to `soft_doc_profiles`
- [x] `soft_compare` wraps `soft_group_compare` + rename
- [x] Soft-lens notebook / tests still produce A2s / A6 tables

## Related

- CIP: 0007
- Branch: `cip0005-depend-multilogue` on ai-dialogue-formats

## Progress Updates

### 2026-10-16

Thin-out applied on formats branch.
