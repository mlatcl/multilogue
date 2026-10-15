---
id: "0002"
title: "Model stages are fingerprint-keyed and replayable"
status: "Implemented"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
related_tenets:
- "reproducibility-via-fingerprints"
stakeholders:
- "paper authors needing canonical runs"
tags:
- "llm"
- "reproducibility"
---

# REQ-0002: Model stages are fingerprint-keyed and replayable

## Description

Every LLM or embedding stage can be checkpointed under a fingerprint of prompt and model, resumed after interruption, and replayed with no API calls when artefacts exist. Fingerprint changes start the stage afresh without silently mixing old and new results.

**Why this matters**: Canonical paper runs must be reproducible (`reproducibility-via-fingerprints`).

**Who benefits**: Authors freezing a reported run; collaborators reproducing results without API keys.

## Acceptance Criteria

- [ ] Stage runner writes append-only JSONL keyed by item plus meta fingerprint
- [ ] Replay mode refuses missing items and fingerprint mismatches
- [ ] Log replay can rebuild results from a call log without new model calls
- [ ] Tests cover resume, supersede-on-fingerprint-change, and replay failure modes without network

## Progress Updates

### 2026-10-15
Requirement created at Ready status from the multilogue package plan.
