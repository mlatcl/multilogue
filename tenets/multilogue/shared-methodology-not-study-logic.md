---
id: "shared-methodology-not-study-logic"
title: "Shared Methodology, Not Study Logic"
status: "Active"
created: "2026-10-15"
last_reviewed: "2026-10-15"
review_frequency: "Annual"
conflicts_with: []
tags:
- tenet
- packaging
- boundaries
---

# Project Tenet: Shared Methodology, Not Study Logic

## Description

Multilogue holds the reusable methodological core shared by public-dialogue analyses: unit contracts, checkpointed LLM stages, phrase extraction primitives, frozen clustering and lenses, document-level weighting, multiverse enumeration, and validation scaffolding. Study-specific I/O (PDF parsers, chatbot `.docx` layouts), prompts, taxonomies, and paper headline metrics belong in consumer packages such as `pub-dialogue` and `ai-dialogue-formats`.

## Quote

*"One method library; many study packages."*

## Examples

- Generic `quote_support` and `StageRunner` live in multilogue; grounds coding stays in dialogue-formats
- Document-weighted bootstrap is general; chatbot-vs-workshop column names stay in the consumer
- Multiverse enumerates arbitrary dimensions; ℓ functions for AI distinctiveness stay in pub-dialogue

## Counter-examples

- Shipping UK technology taxonomies or local-government facilitator names inside multilogue
- Hard-coding Part A / Part B research questions in the library
- Importing consumer packages from multilogue

## Conflicts

- Completeness vs reuse
- Resolution: if a second consumer needs a feature, promote it; otherwise leave it in the study package
