"""Corpus contracts and client protocol.

Consumers (Access) load PDFs, ``.docx``, etc. and hand multilogue units that
conform to these shapes. Multilogue never parses source file formats.
"""
from __future__ import annotations

from typing import Any, Protocol, TypedDict, runtime_checkable


class Unit(TypedDict, total=False):
    """One analysable text span from a dialogue corpus."""

    unit_id: str
    doc_id: str
    text: str
    context: str
    extract_text: str  # text the quote must support; defaults to text if omitted
    meta: dict[str, Any]


class Phrase(TypedDict, total=False):
    """One extracted point attached to a unit."""

    phrase_id: str
    unit_id: str
    doc_id: str
    kind: str
    phrase: str
    quote: str
    quote_support: float
    verified: bool


@runtime_checkable
class LLMClient(Protocol):
    """Minimal surface for completion and embedding backends."""

    def complete(
        self,
        stage: str,
        system: str,
        user: str,
        model: str,
        json_mode: bool = False,
    ) -> str: ...

    def embed(self, texts: list[str], model: str) -> list[list[float]]: ...
