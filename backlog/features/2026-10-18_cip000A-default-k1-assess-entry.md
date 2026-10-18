---
id: "2026-10-18_cip000A-default-k1-assess-entry"
title: "Assess entry defaults to k=1 soft topic"
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
- subject-grain
---

# Task: Assess entry defaults to k=1

## Description

Notebook 03 / Assess helpers start the subject-grain shell from a single soft
topic. Split is the way grain grows. Explicit multi-\(k\) fits remain allowed
when passed in.

## Acceptance Criteria

- [x] Builder / helper fits or wraps \(k{=}1\) for Assess entry
- [x] Prose states start-at-one then split
- [x] Tests cover \(k{=}1\) shell construction
- [x] Notebooks regenerated

## Related

- CIP: 000A

## Progress Updates

### 2026-10-18

Task created; implementation started on `cip000A-grain-sigma2-controls`.
