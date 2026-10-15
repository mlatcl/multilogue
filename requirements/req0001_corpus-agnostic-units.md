---
id: "0001"
title: "Consumers hand units without multilogue knowing source formats"
status: "Ready"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
related_tenets:
- "shared-methodology-not-study-logic"
- "assess-without-the-question"
stakeholders:
- "pub-dialogue maintainers"
- "ai-dialogue-formats maintainers"
tags:
- "access"
- "api"
---

# REQ-0001: Consumers hand units without multilogue knowing source formats

## Description

Study packages load their own corpora (PDFs, `.docx`, and so on) and present multilogue with a common unit and phrase contract. Multilogue does not parse source file formats.

**Why this matters**: Shared methodology stays independent of study I/O (`shared-methodology-not-study-logic`). Access stays outside the library; assess can run on units without source-specific code.

**Who benefits**: Any new dialogue analysis that can produce units with `unit_id`, `doc_id`, and `text`.

## Acceptance Criteria

- [ ] Documented Unit and Phrase contracts (fields and meanings)
- [ ] No PDF or `.docx` parsers inside the `multilogue` package
- [ ] Extract/cluster/weight APIs accept tables or dicts conforming to the contract
- [ ] Consumer migration notes explain how formats and pub-dialogue map into the contract

## Progress Updates

### 2026-10-15
Requirement created at Ready status from the multilogue package plan.
