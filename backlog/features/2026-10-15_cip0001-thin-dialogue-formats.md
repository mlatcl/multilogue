---
id: "2026-10-15_cip0001-thin-dialogue-formats"
title: "Thin ai-dialogue-formats onto multilogue"
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

# Task: Thin dialogue_formats onto multilogue

## Description

Follow-on in the `ai-dialogue-formats` repo: depend on multilogue; re-export or call shared llm/cluster/weight/extract/multiverse; keep docx access, grounds, sequence, Part A/B.

## Acceptance Criteria

- [ ] `dialogue-formats` declares dependency on multilogue
- [ ] No duplicated StageRunner / quote_support / doc_profile implementations
- [ ] Existing formats tests still pass

## Related

- CIP: 0001
- Docs: docs/migration.md
