# multilogue

Reusable Access → Assess → Address methodology for LLM-assisted analysis of public dialogue corpora.

This repository is governed with VibeSafe. Design precedes code:

| Layer | Question | Location |
|-------|----------|----------|
| **WHY** | Guiding principles | [`tenets/multilogue/`](tenets/multilogue/) |
| **WHAT** | Desired outcomes | [`requirements/`](requirements/) |
| **HOW** | Design | [`cip/cip0001.md`](cip/cip0001.md) |
| **DO** | Implementation tasks | [`backlog/`](backlog/) |

CIP-0001 (Accepted) defines the package boundaries relative to `ai-dialogue-formats` and `pub-dialogue`. Fynesse informs AAA philosophically; multilogue does not depend on fynesse at runtime.

Package implementation starts only after this plan is committed; see backlog tasks under CIP-0001.
