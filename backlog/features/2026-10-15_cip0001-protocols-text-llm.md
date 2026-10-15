---
id: "2026-10-15_cip0001-protocols-text-llm"
title: "Implement protocols, text helpers, StageRunner and replay clients"
status: "Ready"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-10-15_cip0001-package-scaffold"]
tags:
- backlog
- cip0001
---

# Task: Protocols, text, LLM runner

## Description

Port and generalise Unit/Phrase contracts, text utilities, StageRunner, ReplayClient, LogClient, and optional OpenAI/litellm adapters from dialogue_formats (REQ-0001, REQ-0002).

## Acceptance Criteria

- [ ] FakeClient tests cover resume, fingerprint supersede, replay miss
- [ ] `quote_support` behaviour preserved
- [ ] Optional extras `multilogue[openai]` and `multilogue[litellm]` declared

## Related

- CIP: 0001
