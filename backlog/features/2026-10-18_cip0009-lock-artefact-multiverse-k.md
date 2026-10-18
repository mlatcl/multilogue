---
id: "2026-10-18_cip0009-lock-artefact-multiverse-k"
title: "CIP-0009: subject-grain lock artefact and formats multiverse k default"
status: "Ready"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
category: "features"
related_cips: ["0009"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0009
- assess
- multiverse
- lock
---

# Task: Subject-grain lock + multiverse \(k\) default

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).

## Description

Define and persist an explicit **locked subject grain** artefact (manifest /
checkpoint fields) that Address consumes: primary \(k\) (or leaf count), fit
fingerprint / responsibilities reference, optional merge–split history, and
`k_multiverse` as hold / \(\pm 1\) only.

Change `run_formats_complexity_demo` so the default factorial multiverse does
**not** use a wide `_default_k_grid`. Default: hold locked / primary \(k\), or
at most `{k-1, k, k+1}`. A wide resolution sweep remains available only via an
explicit `k_grid` argument (one-factor / optional path).

## Acceptance Criteria

- [ ] Lock fields documented and written to run manifest (or equivalent)
- [ ] Formats multiverse default no longer spreads \(k\) enough to dominate
      variance shares on the planted quote/threshold toy
- [ ] Explicit `k_grid=` still allows a deliberate resolution sweep
- [ ] FakeClient / offline formats path stays green

## Implementation Notes

- Retire or demote `_default_k_grid` in `multilogue/experiment.py`.
- Do not pick lock \(k\) by maximising format-gap \(\ell\).
- Coordinate with library merge/split task for history schema if needed.

## Related

- CIP: 0009
- REQ: 000A
- Depends on: none (can land before interactive UI)

## Progress Updates

### 2026-10-18

Task created (Ready) when CIP-0009 Accepted.
