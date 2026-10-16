---
id: "2026-10-15_cip0001-thin-dialogue-formats"
title: "Thin ai-dialogue-formats onto multilogue (CIP-0001 primitives)"
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
- ai-dialogue-formats
---

# Task: Thin dialogue_formats onto multilogue (CIP-0001 primitives)

## Description

Finish consumer adoption in `ai-dialogue-formats` for primitives **already in multilogue** (CIP-0001). Soft PPCA core is already re-exported via CIP-0005 (`soft_lenses.py` → `multilogue.soft`); this task covers the remaining near-duplicate modules.

**Still local (must thin):** `llm.py` (StageRunner / Replay / Log / OpenAIClient), `cluster.py` (Embedder / frozen k-means / lens work), `extract.py` helpers, `multiverse.py` grid shell (call `enumerate_configurations` / `run_multiverse` / `variance_decomposition`), prefer `multilogue.soft.sigma2_sweep_select` over local `sigma2_sweep`, align `as_mapping` with `soft_mapping_from_hard`.

**Keep local:** `Run` / pipeline, docx access, grounds, sequence, Part A/B ℓ, format-specific column renames (`compare`), soft orchestration (`soft_compare`, membership multiverse tables).

Branch: `cip0005-depend-multilogue` (already has multilogue dep + text/stats/soft thin-out).

## Acceptance Criteria

- [ ] `dialogue_formats.llm` re-exports or wraps `multilogue.llm` (+ openai client); no duplicate StageRunner body
- [ ] `cluster` / `extract` call multilogue helpers; study `Run` binding may remain thin wrappers
- [ ] Multiverse shell uses `multilogue.multiverse`; study ℓ callbacks stay local
- [ ] Soft path uses `sigma2_sweep_select` (or documented thin adapter); no divergent PPCA math
- [ ] Existing formats tests pass; parity with prior behaviour preserved for shared helpers

## Implementation Notes

Prefer thin re-exports so notebooks keep `from dialogue_formats…`. See `docs/migration.md` and `docs/cookbooks/ai-dialogue-formats.md`. Gap analysis (2026-10-16): P0 adoption, not new methodology.

## Related

- CIP: 0001, 0005
- Docs: docs/migration.md, docs/cookbooks/ai-dialogue-formats.md
- Repo: mlatcl/ai-dialogue-formats

## Progress Updates

### 2026-10-15

Task created with Proposed status.

### 2026-10-16

Updated after gap analysis: status Ready; soft/text/weight already partially thinned on `cip0005-depend-multilogue`; remaining work is llm/cluster/extract/multiverse.
