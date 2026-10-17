---
id: "2026-10-17_cip0017-mppca-concept-docs"
title: "CIP-0017: concept docs for soft-throughout MPPCA topics"
status: "Ready"
priority: "Medium"
created: "2026-10-17"
last_updated: "2026-10-17"
category: "documentation"
related_cips: ["0001", "0005"]
owner: "Neil Lawrence"
dependencies:
- "2026-10-17_cip0017-mppca-fit-primitive"
tags:
- backlog
- cip0017
- docs
- mppca
---

# Task: MPPCA / soft-throughout concept docs

## Description

Update multilogue concept docs (topic-space / soft-PPCA / address pipeline) so soft phrase→topic (MPPCA, k-means init) is primary; hard labels are a late view; document EMD uses soft mass; lens σ²\* remains a separate fixed floor after selection. State default topic \(\sigma^2\) and the independent-floors decision from pub CIP-0017.

## Acceptance Criteria

- [ ] Concept doc states soft primary / harden-at-boundary
- [ ] Two σ² knobs (topic vs lens) described; each fixed per run/config
- [ ] Cookbook or notebook pointer shows fit → soft histogram → optional harden for labels
- [ ] Hard k-means described as init / legacy view, not the Address default for CIP-0017 consumers

## Related

- CIP: pub-dialogue 0017; multilogue 0001, 0005

## Progress Updates

### 2026-10-17

Task created (Ready).
