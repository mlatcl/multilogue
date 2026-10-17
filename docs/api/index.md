# API overview

Public modules consumers typically import:

| Module | Role |
|--------|------|
| [`multilogue.access`](access.md) | `load` / `list_sources` |
| [`multilogue.assess_base`](assess_base.md) | Question-agnostic tables |
| [`multilogue.extract`](extract.md) | Extraction work fn + phrase tables |
| [`multilogue.cluster`](cluster.md) | Embed, freeze, label, lens |
| [`multilogue.mppca`](mppca.md) | Soft topic MPPCA (CIP-0017); harden-view helpers |
| [`multilogue.soft`](soft.md) | PPCA soft memberships, σ²-by-EMD |
| [`multilogue.distance`](distance.md) | Document EMD, MDS, PERMANOVA |
| [`multilogue.weight`](weight.md) | Document weights, κ, JSD |
| [`multilogue.multiverse`](multiverse.md) | Config grid + variance shares |
| [`multilogue.llm`](llm.md) | `StageRunner`, replay clients |
| [`validate` / `report`](validate_report.md) | Sheets, evidence pack |
| [`dummy` / `experiment`](dummy_experiment.md) | Synthetic CI path |

Top-level re-exports are listed in `multilogue.__all__`.
