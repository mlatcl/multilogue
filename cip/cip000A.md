---
author: "Neil Lawrence"
created: "2026-10-18"
id: "000A"
last_updated: "2026-10-18"
status: "Accepted"
compressed: false
related_requirements: ["000A"]
related_cips: ["0009", "0017"]
tags:
- cip
- assess
- eda
- mppca
- subject-grain
- sigma2
- human-in-the-loop
title: "Assess grain defaults: k=1, EM policy, σ² fix-or-fit"
---

# CIP-000A: Assess grain defaults — k=1, EM policy, σ² fix-or-fit

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

Tighten the CIP-0009 Assess subject-grain shell around three decisions:

1. **Default start at \(k{=}1\)** — one soft bag; grain grows by split.
2. **Document and control EM on merge/split** — what is local, what is global,
   how many iterations (live preview vs Accept).
3. **\(\sigma^2\) fix-or-fit** — once \(k\) is human-chosen, expose whether topic
   noise is held fixed or re-profiled (CIP-0017 grid), with an editable value
   when fixed.

**Which requirements?** Extends REQ-000A (interactive subject grain).

## Motivation

CIP-0009 made \(k\) interactive, but Assess still often *starts* from a
scripted multi-topic fit. That fights the interaction model: the natural
Bishop–Tipping path is one component, then split.

Merge/split already run **full-mixture** EM after a local proposal
(`propose_merge` / `propose_split` → `_fit_from_responsibilities`), with
\(\sigma^2\) held from the parent fit. That behaviour is easy to miss and
expensive on every UI tick. Preview vs Accept need a clear EM budget.

With \(k\) chosen by the analyst, auto-profiling \(\sigma^2\) on every Accept
is coherent (noise should match grain). Blindly re-profiling on every live
preview is not. Analysts also need to **freeze** a \(\sigma^2\) they trust
(pedagogy, reproducibility, comparison across sessions).

## Detailed Description

### 1. Default \(k{=}1\)

| Context | Behaviour |
|---|---|
| Assess shell / notebook 03 entry | Fit (or wrap) a **single** soft topic unless the user overrides |
| Split | Primary way to increase grain |
| Merge | Available once \(k \ge 2\) |

Scripted Layer A paths and Address demos may still pass an explicit \(k\);
pedagogy text should say Assess *starts* at one cluster.

**Initial fit:** `mppca_fit(E, k=1, …)` or `mppca_topics(E, k=1, …)` with the
shell’s \(\sigma^2\) policy (below). Catalogue naming still runs for the
single bag when `label_work` is set.

### 2. EM policy (align with hierarchical MPPCA practice)

Current code (keep, then make knobs + docs match):

| Action | Local proposal | Global refine | Default `max_iter` |
|---|---|---|---|
| **Merge** | Sum soft mass of sources into one column | `_fit_from_responsibilities` on **all** \(k'\) components | 30 (`refit=True`); 1 if `refit=False` |
| **Split** | `mppca_fit` on parent soft support | Redistribute parent mass → full-mixture `_fit_from_responsibilities` | 40 local + 40 global |
| **Live merge preview** | Dry-run merge geometry only | Prefer cheap path: `refit=False` or capped iters — **must not** feel like a full Accept | Cap (e.g. 1–5) |
| **Accept proposal** | Already applied on Propose | Optional extra refine; place for \(\sigma^2\) re-profile | Full budget |

**Tipping / hierarchical note:** Geometry for the dual view remains Bishop–Tipping
local \(U_q\). Optimisation is hierarchical MPPCA-style: **local proposal, then
global EM** with shared \(\sigma^2\). Untouched components are *not* frozen
today — they may move in the global pass. This CIP does **not** require
component freezing unless pedagogy needs it later; it requires the policy to be
documented in the shell status line / notebook prose.

Expose on the shell (constructor + widget):

- `em_max_iter_accept: int` — global EM after Propose/Accept (default 30)
- `em_max_iter_preview: int` — live merge preview (default 1)
- Status text shows last `n_iter` from the fit after each edit

### 3. \(\sigma^2\) fix-or-fit

| Mode | Meaning |
|---|---|
| **fixed** | Use the numeric \(\sigma^2\) in the control; EM never changes it |
| **profile** | On **Accept** (and on initial \(k{=}1\) fit if requested), run CIP-0017 `profile_topic_sigma2` at current \(k\), then EM at \(\sigma^{2*}\) |

Widget (Layer B):

- Dropdown: `σ² mode` ∈ {fixed, profile}
- Float text / bounded float: current \(\sigma^2\) (editable in **fixed**;
  read-only or refreshed after profile in **profile**)
- Button optional: “Re-profile σ² now” (runs profile without requiring a
  merge/split)

Rules:

- Live merge/split **preview** never re-profiles \(\sigma^2\).
- **Propose** merge/split keeps \(\sigma^2\) unless mode is profile *and* we
  choose to re-profile only on **Accept** (recommended default: re-profile on
  Accept only).
- Lock artefact records `sigma2` and `sigma2_mode` (`fixed` | `profile`).

Initial Assess entry:

- If mode **profile**: `profile_topic_sigma2(E, k=1, …)` then shell.
- If mode **fixed**: `mppca_fit(E, k=1, sigma2=value, …)`.

### Stage boundary

Unchanged from CIP-0009: grain interaction is **Assess**; lenses / \(\ell\) /
multiverse remain **Address** under the lock.

## Implementation Plan

1. **Defaults & Layer A**
   - Notebook 03 / builder: start Assess at \(k{=}1\); prose explains split-to-grow.
   - Helpers to build initial fit under fix/profile \(\sigma^2\).

2. **EM knobs**
   - Thread `max_iter` / preview vs accept through `propose_*` and shell.
   - Live merge preview uses capped / `refit=False` path.
   - Surface `n_iter` in status HTML.

3. **σ² widget**
   - Shell state: `sigma2_mode`, `sigma2_value`.
   - Dropdown + value box; re-profile on Accept when mode is profile.
   - Persist mode + value on `lock()`.

4. **Tests & notebooks**
   - Unit tests: \(k{=}1\) start; preview does not call profile; Accept with
     profile updates \(\sigma^2\); fixed mode holds value across merge.
   - Regenerate notebooks via `scripts/build_notebooks.py`.

## Backward Compatibility

- Callers that pass an explicit multi-\(k\) fit into `SubjectGrainShell` still
  work.
- `propose_merge` / `propose_split` keep current signatures; new kwargs are
  optional with today’s defaults until preview capping lands.
- Address / formats demos unchanged unless they opt into Assess \(k{=}1\).

## Testing Strategy

- `tests/test_subject_grain.py` — EM iter caps; \(\sigma^2\) preserved vs
  re-profiled.
- `tests/test_subject_grain_shell.py` — mode/value on lock; preview path cheap.
- Smoke: notebook 03 Layer A starts at \(k{=}1\).

## Related Requirements

- [REQ-000A](../requirements/req000A_interactive-subject-grain.md) — interactive
  subject grain (extended by this HOW).

## Implementation Status

- [ ] Default Assess entry at \(k{=}1\) (builder + helpers)
- [ ] EM preview vs accept budgets wired through shell
- [ ] \(\sigma^2\) fix/profile controls + lock metadata
- [ ] Tests
- [ ] Notebooks regenerated

## References

- Bishop & Tipping, hierarchical visualisation / mixtures of PPCA (TPAMI 1998)
- CIP-0009 — interactive subject grain shell
- CIP-0017 — topic \(\sigma^2\) profile grid
- `multilogue/subject_grain.py` — `propose_merge`, `propose_split`,
  `_fit_from_responsibilities`
- `multilogue/mppca.py` — `profile_topic_sigma2`, `mppca_fit`
