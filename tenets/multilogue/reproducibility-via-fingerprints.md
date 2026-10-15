---
id: "reproducibility-via-fingerprints"
title: "Reproducibility via Fingerprints and Replay"
status: "Active"
created: "2026-10-15"
last_reviewed: "2026-10-15"
review_frequency: "Annual"
conflicts_with: []
tags:
- tenet
- reproducibility
---

# Project Tenet: Reproducibility via Fingerprints and Replay

## Description

Every model stage is keyed by a fingerprint of prompt text and model identity. Checkpoints are append-only JSONL. Replay mode reproduces a canonical run with no API calls and refuses fingerprint drift. Cluster assignments are frozen when the phrase set is unchanged, because k-means is not bit-for-bit stable across machines even with a fixed seed.

## Quote

*"If the fingerprint moved, the stage did not replay — it restarted."*

## Examples

- Changing a prompt supersedes the old checkpoint rather than silently mixing results
- Replay raises when an item has no saved result
- Frozen `cluster_assignments_k{k}.csv` reused across machines

## Counter-examples

- Re-running extraction without recording prompt hashes
- Treating random-seed k-means as cross-machine reproducible without saved labels
- Editing checkpoints by hand without invalidating the fingerprint

## Conflicts

- Cost of re-extraction vs fidelity
- Resolution: fingerprint mismatch forces a fresh stage; old results are kept as superseded artefacts
