---
id: "2026-10-15_cip0001-thin-pub-dialogue"
title: "Thin pub-dialogue onto multilogue"
status: "Proposed"
priority: "Medium"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-10-15_cip0001-multiverse-validate-report"]
tags:
- backlog
- cip0001
- consumer
---

# Task: Thin pub_dialogue onto multilogue

## Description

Follow-on in the `pub-dialogue` repo: depend on multilogue for StageRunner-style stages, clustering primitives, multiverse enumerate/variance; keep PDF access, crosscut, distance, temporal ℓ, PPCA lenses.

## Acceptance Criteria

- [ ] `pub-dialogue` declares dependency on multilogue
- [ ] Study modules (crosscut, distance, address PDF path) remain local
- [ ] Existing pub-dialogue tests still pass

## Related

- CIP: 0001
- Docs: docs/migration.md
