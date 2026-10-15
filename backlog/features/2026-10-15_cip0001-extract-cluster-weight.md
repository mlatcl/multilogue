---
id: "2026-10-15_cip0001-extract-cluster-weight"
title: "Implement generic extract, frozen cluster/lenses, document weighting"
status: "Ready"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-10-15_cip0001-protocols-text-llm"]
tags:
- backlog
- cip0001
---

# Task: Extract, cluster, weight

## Description

Generic phrase extraction, Embedder + frozen k-means + lens helpers, and document-level weighting APIs (REQ-0003, REQ-0004).

## Acceptance Criteria

- [ ] Extract accepts kind/template/sentinel and optional quote threshold
- [ ] Frozen assignments round-trip when phrase ids match
- [ ] `group_compare` has no hard-coded chatbot/workshop columns
- [ ] Synthetic tests pass without API

## Related

- CIP: 0001
