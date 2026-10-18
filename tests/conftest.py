"""Shared pytest fixtures — keep tests offline even if the developer has a .env key."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_fake_llm(monkeypatch):
    monkeypatch.setenv("MULTILOGUE_FORCE_FAKE", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
