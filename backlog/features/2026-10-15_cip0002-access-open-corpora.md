---
id: "2026-10-15_cip0002-access-open-corpora"
title: "Implement pods-style Access loaders for public civic corpora"
status: "Completed"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0002"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0002
- access
---

# Task: Access open-corpus loaders

## Description

Implement `multilogue.access` with download/cache helpers and named loaders (`synthetic`, `polis`, `gdn_cc`, `cdcp`, `cimt`, `decidim`) returning Unit bundles. Fixture tests without network; cache gitignored.

## Acceptance Criteria

- [x] `load` / `list_sources` switch between sources
- [x] Each listed source parses to units
- [x] Licence override for CI
- [x] README documents usage
- [x] Pytest green offline

## Related

- CIP: 0002

## Progress Updates

### 2026-10-15

Implemented `multilogue/access/` (download + datasets + resources.json). 35 tests passing. Polis smoke download confirmed under gitignored `data/cache/`.
