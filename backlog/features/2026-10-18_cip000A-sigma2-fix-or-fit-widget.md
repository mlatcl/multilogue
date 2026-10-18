---
id: "2026-10-18_cip000A-sigma2-fix-or-fit-widget"
title: "σ² fixed vs profile controls on Assess shell"
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
- sigma2
---

# Task: σ² fixed vs profile controls

## Description

Add shell state and Layer B widgets for \(\sigma^2\) mode (fixed | profile) and
value. Re-profile on Accept when mode is profile; never on live preview. Persist
mode + value on lock.

## Acceptance Criteria

- [x] Dropdown + value control on widgets()
- [x] Accept re-profiles when mode=profile; fixed holds value across merge/split
- [x] Lock artefact includes sigma2_mode
- [x] Tests cover both modes

## Related

- CIP: 000A

## Progress Updates

### 2026-10-18

Task created; implementation started.
