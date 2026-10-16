---
id: "0007"
title: "Published documentation lets a new consumer package depend on multilogue without reading the source"
status: "Implemented"
priority: "High"
created: "2026-10-16"
last_updated: "2026-10-16"
related_tenets:
- "shared-methodology-not-study-logic"
stakeholders:
- "pub-dialogue maintainers"
- "ai-dialogue-formats maintainers"
- "new study authors"
tags:
- "documentation"
- "onboarding"
---

# REQ-0007: Published documentation lets a new consumer package depend on multilogue without reading the source

## Description

Installable documentation explains the Access → Assess → Address method, the Unit/Phrase contracts, the stage-runner model, and worked recipes sufficient to stand up consumer packages in the style of `ai-dialogue-formats` and `pub-dialogue` — without shipping private corpora or study prompts.

**Why this matters**: The shared library only earns its keep if a third study can adopt it from docs, not from reverse-engineering notebooks.

**Who benefits**: Maintainers thinning existing study repos, and authors of new dialogue analyses.

## Acceptance Criteria

- [x] A modern static site builds from Markdown in-repo (`mkdocs build` succeeds)
- [x] Contracts, AAA stages, and checkpoints are documented with runnable synthetic examples
- [x] Cookbooks show how to structure an `ai-dialogue-formats`-style package and a `pub-dialogue`-style package on top of multilogue
- [x] API reference covers the public modules a consumer needs
- [x] README links to the docs entry point; no private dialogue text appears in docs

## Non-Goals

- Hosting study PDFs or participant quotes
- Replacing pedagogical Colab notebooks (they complement the site)
- Auto-generated Sphinx from every private symbol
