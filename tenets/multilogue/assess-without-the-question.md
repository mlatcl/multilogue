---
id: "assess-without-the-question"
title: "Assess Without the Question"
status: "Active"
created: "2026-10-15"
last_reviewed: "2026-10-15"
review_frequency: "Annual"
conflicts_with: []
tags:
- tenet
- assessment
- fynesse
---

# Project Tenet: Assess Without the Question

## Description

Multilogue follows the Fynesse Access → Assess → Address separation. Assessment characterises a dialogue corpus — sizes, coverage, quality flags, vocabulary — without invoking extraction prompts, clustering choices, or research questions. That keeps assess outputs reusable across studies that share a corpus shape, and keeps question-specific work auditable in Address.

## Quote

*"Assess is only work you can do without the question in mind."*

## Examples

- Reporting unit lengths and documents per group before any LLM call
- Flagging empty or bibliography-like chunks without filtering them for a particular theme
- Vocabulary frequency diagnostics that do not encode concern/benefit taxonomies

## Counter-examples

- Running concern extraction inside an assess notebook cell
- Dropping units in assess because they are irrelevant to AI distinctiveness
- Mixing format-comparison logic into corpus quality plots

## Conflicts

- Speed of prototyping vs separation
- Resolution: explore in scratch notebooks; enforce the boundary before code enters the package
