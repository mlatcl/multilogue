# Migrating consumers onto multilogue

CIP-0001 landed the library; CIP-0004 documents how to recreate or thin consumers. Follow-on backlog work lives in each study repo.

For greenfield packages, prefer the [cookbooks](cookbooks/consumer-skeleton.md) over this thinning map.

## `ai-dialogue-formats` → multilogue

| Current module | Move / call | Keep in dialogue_formats |
|----------------|-------------|--------------------------|
| `text.quote_support`, `sha`, `parse_json` | `multilogue.text` | — |
| `llm.StageRunner`, `ReplayClient`, `LogClient` | `multilogue.llm` | study-specific `OpenAIClient` wiring in `pipeline.Run` (or use `multilogue.openai_client`) |
| `stats.doc_profile`, bootstrap, `jsd`, `kappa` | `multilogue.weight` | format-named wrappers if desired |
| `extract` parse/yield helpers | `multilogue.extract` | `TYPES`, `render` with format frames, prompts |
| `cluster.Embedder`, frozen assignments, lenses | `multilogue.cluster` | format columns in `cluster_table` |
| `multiverse` | `multilogue.multiverse` + Part B ℓ callbacks | experience-gap configs |
| `validate` sheets/κ | `multilogue.validate` + local grounds | grounds, own-words, word list |
| `report.evidence_pack` | `multilogue.report` | confidentiality notes |
| `access`, `grounds`, `sequence`, `compare` | — | stay |

Dependency: add `multilogue` (path or published) to `pyproject.toml`. Prefer thin re-exports during transition so notebooks keep importing `dialogue_formats.*`.

## `pub-dialogue` → multilogue

| Current module | Move / call | Keep in pub_dialogue |
|----------------|-------------|----------------------|
| Checkpoint / client patterns | `StageRunner` + `LiteLLMClient` | `AccessStage` PDF chunking |
| Extraction diagnostics | `extract.yield_report` / `phrase_table` | tech-term filters, concern/benefit prompts |
| Clustering / labelling helpers | `multilogue.cluster` | address orchestration |
| Soft PPCA / σ² sweep / run EMD | `multilogue.soft` | thin wrappers if desired |
| Document EMD / MDS / PERMANOVA | `multilogue.distance` | group column wiring |
| Multiverse enumerate + variance | `multilogue.multiverse` | R1–R3 ℓ, k/prompt artefact loading |
| Evidence pack | `multilogue.report` | study-specific columns |
| `crosscut`, temporal | — | stay |
| Assess quality plots | optionally `assess_base` | bibliography/table heuristics |

## Suggested order

1. multilogue v0.1 installable with tests (this repo)
2. Thin `dialogue_formats` (cleaner module split already)
3. Thin `pub_dialogue` (keep large `address.py` study logic; replace shared primitives)

Backlog: `2026-10-15_cip0001-thin-dialogue-formats`, `2026-10-15_cip0001-thin-pub-dialogue`.
