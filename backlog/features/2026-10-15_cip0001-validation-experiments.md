---
id: "2026-10-15_cip0001-validation-experiments"
title: "Synthetic-data validation experiments for multilogue core"
status: "Completed"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips: ["0001"]
owner: "Neil Lawrence"
dependencies: ["2026-10-15_cip0001-methodology-docs"]
tags:
- backlog
- cip0001
- validation
---

# Task: Synthetic validation experiments

## Description

Add in-repo validation that exercises extract → embed → cluster → weight → multiverse using **only synthetic units**. No real dialogue transcripts or reports enter this repository.

## Acceptance Criteria

- [x] `multilogue.dummy` provides phrase bank, `make_units()`, and `FakeClient`
- [x] CLI/script runs an end-to-end experiment writing only under gitignored `outputs/`
- [x] Pytest covers the experiment path (tmp dirs; no API; no personal data)
- [x] README documents how to run the experiment

## Related

- CIP: 0001

## Progress Updates

### 2026-10-15

Implemented `multilogue/dummy.py`, `multilogue/experiment.py`, `multilogue-validate` entry point, and `tests/test_experiment.py`. Smoke run wrote tables under gitignored `outputs/`; full suite 24 passed.
