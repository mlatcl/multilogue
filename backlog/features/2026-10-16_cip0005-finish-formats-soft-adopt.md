---
id: "2026-10-16_cip0005-finish-formats-soft-adopt"
title: "Finish / merge CIP-0005 soft adopt in ai-dialogue-formats"
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
- ai-dialogue-formats
---

# Task: Finish / merge CIP-0005 soft adopt in ai-dialogue-formats

## Description

CIP-0005 follow-on: land the `cip0005-depend-multilogue` branch so formats depends on `multilogue[distance]`, soft PPCA comes from `multilogue.soft`, and parity tests stay green. Study soft orchestration (`soft_compare`, membership multiverse tables) stays in `soft_lenses.py`.

## Acceptance Criteria

- [ ] `pyproject.toml` depends on `multilogue[distance]` (git or published)
- [ ] `soft_lenses` / `text` / `stats` use multilogue for shared math (no duplicate PPCA)
- [ ] Soft-lens tests pass with POT; scipy-vs-POT EMD within ~1e-6 where applicable
- [ ] Branch reviewed and merged (or ready for PR)

## Implementation Notes

Parity vs pre-retrofit `HEAD` already checked (2026-10-16): mixture, σ²\*, curve support match; EMD ≤ 1e-8. Remaining: commit/PR hygiene, optional `sigma2_sweep_select` instead of local sweep loop (can share with CIP-0001 thin task).

## Related

- CIP: 0005
- Branch: `cip0005-depend-multilogue` on mlatcl/ai-dialogue-formats
- Related: `2026-10-15_cip0001-thin-dialogue-formats`

## Progress Updates

### 2026-10-16

Task created. Soft/text/stats thin-out implemented on branch; tests + parity green.
