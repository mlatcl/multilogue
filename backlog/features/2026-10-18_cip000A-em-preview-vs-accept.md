---
id: "2026-10-18_cip000A-em-preview-vs-accept"
title: "EM budgets for merge/split preview vs accept"
status: "Completed"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["000A"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- assess
- mppca
---

# Task: EM budgets for preview vs accept

## Description

Wire `em_max_iter_preview` and `em_max_iter_accept` through the shell so live
merge preview stays cheap while Propose/Accept run full-mixture EM. Surface
last `n_iter` in status.

## Acceptance Criteria

- [x] Live merge preview uses capped / non-refit EM
- [x] Propose merge/split use accept budget
- [x] Status shows EM iters after edits
- [x] Unit tests for preview vs accept iter paths

## Related

- CIP: 000A

## Progress Updates

### 2026-10-18

Task created; implementation started.
