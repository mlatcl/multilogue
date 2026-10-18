"""Resolve a study LLM client from the environment.

Interactive notebooks and demos prefer a live OpenAI client when
``OPENAI_API_KEY`` is set (via ``.env`` or the shell). CI / offline smoke
forces FakeClient with ``MULTILOGUE_FORCE_FAKE=1``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Human-facing topic catalogue prompt (English titles for the analyst).
TOPIC_LABEL_SYSTEM = (
    "You name soft topic clusters for human analysts. "
    "Always write label and description in English, even when the phrases "
    "are in another language. Reply with a single JSON object only."
)

TOPIC_LABEL_PROMPT = (
    "Summarise this soft topic for a human analyst. "
    "Return JSON with keys label and description. "
    "label: ONE short English title (at most six words) — translate if the "
    "phrases are not in English; not an id, hash, list, sentiment tag, or '?'. "
    "description: ONE English sentence explaining what the phrases have in common.\n"
    "Phrases:\n<<PHRASES>>"
)

OPENAI_MODELS = {
    "embed": "text-embedding-3-small",
    "label": "gpt-4.1-mini",
    "extract": "gpt-4.1-mini",
}

FAKE_MODELS = {
    "embed": "fake-emb",
    "label": "fake-small",
    "extract": "fake-small",
}

# Models offered in the subject-grain labelling UI (OpenAI Responses-compatible).
LABEL_MODEL_CHOICES = (
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "o4-mini",
    "fake-small",
)


def label_stage_fingerprint(
    model: str,
    *,
    system: str = TOPIC_LABEL_SYSTEM,
    prompt: str = TOPIC_LABEL_PROMPT,
    extra: str = "",
) -> str:
    """StageRunner fingerprint that *includes* prompt text (busts label cache)."""
    parts = ["labels", str(model), str(system), str(prompt)]
    if extra:
        parts.append(str(extra))
    return "|".join(parts)


def _force_fake() -> bool:
    return os.environ.get("MULTILOGUE_FORCE_FAKE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def resolve_study_client(
    *,
    log_path: str | Path | None = None,
    prefer_openai: bool = True,
    allow_fake: bool | None = None,
) -> tuple[Any, dict[str, str], str]:
    """Return ``(client, models, kind)`` with ``kind`` in ``{"openai", "fake"}``.

    Loads ``.env`` via :func:`multilogue.config.load_dotenv` (cwd and parents,
    so a notebook under ``notebooks/`` still finds the repo-root ``.env``).

    Uses :class:`~multilogue.openai_client.OpenAIClient` when ``OPENAI_API_KEY``
    is set and FakeClient is not forced. FakeClient is used *only* when
    ``MULTILOGUE_FORCE_FAKE=1`` (or ``allow_fake=True``). Missing key without
    an explicit offline force raises — it does **not** silently default to fake.
    """
    from .config import load_dotenv

    env_path = load_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    force = _force_fake()
    if allow_fake is None:
        allow_fake = force
    if prefer_openai and key and not force:
        from .openai_client import OpenAIClient

        client = OpenAIClient(log_path=Path(log_path) if log_path else None)
        return client, dict(OPENAI_MODELS), "openai"
    if force or allow_fake:
        from .dummy import FakeClient

        return FakeClient(), dict(FAKE_MODELS), "fake"
    searched = "cwd and parents"
    if env_path is not None:
        searched = str(env_path)
    raise RuntimeError(
        "No OPENAI_API_KEY for a live study client "
        f"(looked in {searched}). Set the key in a repo-root .env, or set "
        "MULTILOGUE_FORCE_FAKE=1 for the offline FakeClient path "
        "(CI / smoke only)."
    )
