---
id: "0009"
title: "Unit text can be assessed for length and character sanity before Address"
status: "In Progress"
priority: "High"
created: "2026-10-18"
last_updated: "2026-10-18"
related_tenets:
- "assess-without-the-question"
stakeholders:
- "multilogue maintainers"
- "formats and pub-dialogue notebook users"
tags:
- "assess"
- "diagnostics"
- "pedagogy"
---

# REQ-0009: Unit text can be assessed for length and character sanity before Address

## Description

Before any LLM extraction or embedding, analysts can characterise loaded units
with question-agnostic diagnostics: unit (paragraph) length, sentence length,
word-length distribution (with a light language hint), and character-class /
unusual-codepoint inventory, including histograms and flags for extremes.

Pedagogical notebooks teach those diagnostics in Assess, explain what extract
LLM calls and phrase embeddings do in Address, and the formats notebook runs
the Assess gate on real units before paying for Address.

**Why this matters**: Assess must remain reusable without the research question
(`assess-without-the-question`). Jumping from Access to Address without length
and character checks hides OCR debris, empty chunks, and language-mismatched
text until after API spend.

**Who benefits**: Anyone running the pedagogical series or a formats-style
pipeline on public or consumer corpora.

## Acceptance Criteria

- [ ] Library helpers return tables and flags for unit, sentence, word-length,
      and character-class diagnostics without LLM or question-specific filters
- [ ] Visualisations exist for the main length and character-class summaries
- [ ] Notebook 01 teaches the diagnostics; notebook 02 explains extract calls
      and phrase embedding; notebook 09 runs Assess on the format pair before Address
- [ ] Offline smoke path (synthetic / FakeClient) remains green

## Notes

Language handling is a light heuristic (`de` / `en` / `auto`), not a full
language-ID stack. Fixing bad PDF chunking itself is Access follow-on work.

## References

- **Related Tenets**: assess-without-the-question
- **CIP**: 0008

## Progress Updates

### 2026-10-18
Requirement created alongside CIP-0008.
