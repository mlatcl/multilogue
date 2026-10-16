# Multilogue methodology

Multilogue packages the reusable analytic method shared by public-dialogue studies that follow Fynesse **Access → Assess → Address**. It is a library, not a paper: consumers supply corpora, prompts, and headline metrics.

## Access → Assess → Address

| Stage | Responsibility in multilogue | Belongs in consumers |
|-------|------------------------------|----------------------|
| **Access** | Unit / Phrase contracts; optional pods-style loaders for **public** civic corpora (`multilogue.access.load`) | PDF/`.docx` parsers and private study I/O |
| **Assess** | Size/coverage/vocabulary helpers with no LLM | Corpus-specific quality plots |
| **Address** | Extract, embed, cluster, weight, multiverse, validation scaffolding | Study prompts, grounds, cross-cutting, temporal ℓ |

Assess remains question-agnostic: *"Assess is only work you can do without the question in mind."*

## Shared analytic steps

1. **Phrase extraction** — narrow passes keyed by kind, with sentinel replies and optional quote verification (`quote_support`).
2. **Shared topic space** — embed phrases; k-means with **frozen** assignments when the phrase set is unchanged; blind labels; framing lenses.
3. **Document-level weighting** — shares average over documents; bootstrap resamples documents; temporal presence can use document-level binary weighting.
4. **Multiverse** — Cartesian product of analytic choices; consumers supply evaluation callbacks (ℓ); report variance shares by dimension (Bell, Kampman, Dodge & Lawrence, 2022).
5. **Validation scaffolding** — stratified sampling for blind sheets, κ / rank agreement, evidence-pack HTML shell (no study coding schemes).

## Reproducibility

Model stages run through `StageRunner`: append-only JSONL checkpoints keyed by item, meta fingerprint of prompt + model, resume on rerun, supersede on fingerprint change, and replay with no API calls.

## Design choices worth knowing

| Choice | Why |
|--------|-----|
| Small unit contract | Downstream code must not know PDF vs Polis vs synthetic |
| Frozen k-means | Assignments are not bit-stable across machines; freeze when the phrase set is unchanged |
| Document weights | Long documents must not drown short ones in pooled phrase counts |
| ℓ as a callback | Paper metrics stay out of the library |
| PCA plots as *views* | Classical PCA summarises variance for diagnostics; probabilistic PCA / soft lenses stay in study Address code |

## Non-goals

- Study PDF/`.docx` parsers (public open-data CSV/JSON/TSV→Unit adapters are allowed under Access)
- Prompts, taxonomies, local identifying names
- Paper-specific headline metrics (AI distinctiveness, format experience gaps, etc.)
- Runtime dependency on the fynesse install stubs
- Shipping private dialogue corpora in the repository
