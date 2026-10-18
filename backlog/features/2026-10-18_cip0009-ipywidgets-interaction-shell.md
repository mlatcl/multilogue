---
id: "2026-10-18_cip0009-ipywidgets-interaction-shell"
title: "CIP-0009: ipywidgets subject-grain interaction shell (Layer B)"
status: "Ready"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-18_cip0009-topic-fit-viz-catalogue-merge-split"
- "2026-10-18_cip0009-lock-artefact-multiverse-k"
tags:
- backlog
- cip0009
- assess
- ipywidgets
- ux
---

# Task: ipywidgets subject-grain interaction shell

> **Note**: Layer B of CIP-0009. Sits on Layer A model/viz APIs.

## Description

Build a notebook **interaction shell** so analysts can try merge/split
combinations live: geometry updates immediately; LLM names refresh
**on demand** for dirty topics only.

Widget surface (v1):

- Multi-select topics → **Merge**
- Dropdown topic → **Split**
- **Undo** (history stack)
- **Name dirty topics** (StageRunner / label client; only affected bags)
- **Lock** (write subject-grain artefact)
- Outputs: fit figure + catalogue (mark stale/unnamed dirty rows)

`ipywidgets` is an **optional** extra: import-guard; core multilogue must
import without it. No click-on-canvas hit-testing in this task.

## Acceptance Criteria

- [ ] Shell state machine supports merge / split / undo / dirty set / lock
- [ ] Merge/Split/Undo always refresh the fit view without calling the LLM
- [ ] LLM labelling runs only via explicit “Name dirty topics” (or documented
      toggle), and only for dirty ids
- [ ] Lock invokes Layer A `lock_subject_grain` (or equivalent)
- [ ] Importing multilogue succeeds when `ipywidgets` is absent
- [ ] Unit tests cover dirty/undo logic without requiring a display frontend

## Implementation Notes

- Depend on Layer A helpers; do not re-implement MPPCA in the widget module.
- Colab-friendly: buttons + selectors, not matplotlib pick events.
- FakeClient-compatible label hook for pedagogy.

## Related

- CIP: 0009
- REQ: 000A
- Depends on: Layer A viz/merge/split; lock artefact task
- Follow-on: notebook Assess section mounts this shell

## Progress Updates

### 2026-10-18

Task created after CIP-0009 interaction-shell design amendment.
