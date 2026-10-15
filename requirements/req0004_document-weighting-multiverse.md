---
id: "0004"
title: "Document weighting and multiverse variance shares are first-class"
status: "Implemented"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
related_tenets:
- "document-level-weighting"
- "shared-methodology-not-study-logic"
stakeholders:
- "robustness / multiverse analyses"
tags:
- "statistics"
- "multiverse"
---

# REQ-0004: Document weighting and multiverse variance shares are first-class

## Description

Theme shares average over documents with bootstrap uncertainty. Temporal presence can use document-level binary weighting. Analytic choices enumerate as a Cartesian product; consumers supply evaluation callbacks; variance shares by dimension are reported (Bell et al. 2022 style).

**Why this matters**: Document-level weighting and multiverse reporting are core shared method, not paper-specific glue.

**Who benefits**: Both papers' robustness sections; future studies with different grouping variables.

## Acceptance Criteria

- [ ] `doc_profile` / `group_compare` / `doc_binary_presence` APIs with configurable document and group columns
- [ ] `enumerate_configurations`, callback `run_multiverse`, and `variance_decomposition`
- [ ] No hard-coded chatbot/workshop or paper ℓ metrics inside multilogue
- [ ] Unit tests with synthetic phrase tables

## Progress Updates

### 2026-10-15
Requirement created at Ready status from the multilogue package plan.
