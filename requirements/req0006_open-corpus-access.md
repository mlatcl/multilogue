---
id: "0006"
title: "Users can load public civic corpora as units via a switchable Access API"
status: "Implemented"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
related_tenets:
- "shared-methodology-not-study-logic"
- "assess-without-the-question"
stakeholders:
- "multilogue maintainers"
- "validation experiment users"
tags:
- "access"
- "api"
- "open-data"
---

# REQ-0006: Switchable open-corpus Access loaders

## Description

Multilogue provides an Access-layer API to download (or cache) selected **public** civic corpora and present them as `Unit` lists. Users switch sources by name (pods-style), without committing dialogue data to the repository. Study-specific PDF/`.docx` parsers remain in consumer packages.

**Why this matters**: Validation and demos need real-world civic text under open licences, while private study corpora stay out of multilogue.

## Acceptance Criteria

- [x] Named sources are listed and loadable via a single switch (`load(source, ...)`)
- [x] Each source returns units conforming to the Unit contract, plus citation/licence metadata
- [x] Downloads land only under a configurable, gitignored cache directory
- [x] Licence acknowledgement can be automated for CI (`override_manual_authorize`)
- [x] No private dialogue corpora are shipped in the package

## Progress Updates

### 2026-10-15
Requirement created with CIP-0002; implemented via `multilogue.access`.
