---
id: "2026-10-15_cip0001-thin-pub-dialogue"
title: "Thin pub-dialogue onto multilogue (CIP-0001 primitives)"
status: "Ready"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-16"
category: "features"
related_cips: ["0001", "0005"]
owner: "Neil Lawrence"
dependencies: ["2026-10-15_cip0001-multiverse-validate-report"]
tags:
- backlog
- cip0001
- cip0005
- consumer
- pub-dialogue
---

# Task: Thin pub_dialogue onto multilogue (CIP-0001 primitives)

## Description

Finish consumer adoption in `pub-dialogue` for primitives **already in multilogue**. Soft PPCA + document EMD are already thin-wrapped (CIP-0005). This task covers CIP-0001 shells still reinvented locally.

**Still local (must thin / adopt):**

- `multiverse.variance_decomposition` — near-copy of `multilogue.multiverse.variance_decomposition`; switch import
- Prefer `enumerate_configurations` / callback `run_multiverse` where the study grid allows
- Optional later: StageRunner once LiteLLM client shape matches (`complete(stage, system, user, model)`); not blocking for variance thin-out

**Keep local:** PDF/OCR access, `crosscut`, tech-term filters, concern/benefit prompts, temporal / GenAI windows, paper ℓ R1–R3, study evidence packs, Address orchestration.

**Do not** keep PPCA/EMD local — already delegated (see CIP-0005 tasks).

Branch: `cip0005-depend-multilogue`.

## Acceptance Criteria

- [ ] Pub multiverse imports variance decomposition (and enumerate where applicable) from multilogue; local copy removed
- [ ] Soft / distance remain thin wrappers over `multilogue.soft` / `multilogue.distance`
- [ ] Crosscut, access parsers, paper ℓ remain local
- [ ] Existing pub-dialogue tests pass (`test_distance`, `test_multiverse_sigma2`, …)

## Implementation Notes

Stale CIP-0001 wording said “keep distance / PPCA local” — superseded by CIP-0005. Client adapter for StageRunner is optional follow-on (gap analysis P3).

## Related

- CIP: 0001, 0005
- Docs: docs/migration.md, docs/cookbooks/pub-dialogue.md
- Repo: mlatcl/pub-dialogue

## Progress Updates

### 2026-10-15

Task created with Proposed status.

### 2026-10-16

Updated after gap analysis: status Ready; soft/distance thin-out done on branch; remaining CIP-0001 gap is multiverse shell (+ optional StageRunner).
