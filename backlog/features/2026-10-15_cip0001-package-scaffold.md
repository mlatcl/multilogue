---
id: "2026-10-15_cip0001-package-scaffold"
title: "Scaffold multilogue package, pyproject, README, tests layout"
status: "In Progress"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: []
tags:
- backlog
- cip0001
---

# Task: Package scaffold

## Description

Add `pyproject.toml`, empty/stub `multilogue/` modules, `tests/`, and a real README describing methodology contract and non-goals.

## Acceptance Criteria

- [ ] `pip install -e ".[dev]"` works
- [ ] README states AAA contract and what stays in consumers
- [ ] Package importable as `import multilogue`

## Related

- CIP: 0001

## Progress Updates

### 2026-10-15

Task created; implementation starting.
