# multilogue

**Reusable Access → Assess → Address methodology** for LLM-assisted analysis of public dialogue corpora.

Multilogue is a library, not a paper. Study packages supply corpora, prompts, and headline metrics. This package supplies the shared method: unit contracts, resumable model stages, frozen clustering, document-weighted comparisons, and multiverse variance shares.

## Why three aspects?

| Aspect | What it is for | What it must not do |
|--------|----------------|---------------------|
| **Access** | Make text electronically usable under a unit contract | Encode the research question |
| **Assess** | Characterise quality and coverage anyone could reuse | Call LLMs or filter for a specific finding |
| **Address** | Answer a question (extract, cluster, weight, ℓ) | Own study PDF parsers or paper-specific metrics |

> Assess is only work you can do without the question in mind.

## Start here

1. [Getting started](getting-started.md) — install and a five-minute synthetic run
2. [Methodology](methodology.md) — the shared analytic steps
3. [Cookbooks](cookbooks/consumer-skeleton.md) — stand up a consumer package
4. [Pedagogical notebooks](notebooks.md) — Colab walkthroughs with plots

## Consumer targets

| Cookbook | Pattern |
|----------|---------|
| [ai-dialogue-formats style](cookbooks/ai-dialogue-formats.md) | Compare dialogue *formats*; keep format frames and experience metrics local |
| [pub-dialogue style](cookbooks/pub-dialogue.md) | Multi-technology consultations; keep PDF access and paper ℓ local |

Both cookbooks use **synthetic data only**. Private transcripts never enter this repository.

## Non-goals

- PDF / `.docx` parsers (except optional *public* open-data CSV/JSON loaders)
- Study prompts, grounds taxonomies, paper headline metrics
- Shipping participant dialogue in git
