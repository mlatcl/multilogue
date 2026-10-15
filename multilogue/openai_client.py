"""Optional OpenAI adapter. Install with ``pip install multilogue[openai]``."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from .llm import utcnow
from .text import sha


class OpenAIClient:
    """OpenAI Responses API + embeddings."""

    def __init__(
        self,
        log_path: Path | None = None,
        api_key: str | None = None,
        reasoning_effort: str = "medium",
    ):
        from openai import OpenAI

        if api_key is None and not os.environ.get("OPENAI_API_KEY"):
            from .config import load_dotenv

            load_dotenv()
        self._c = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.reasoning_effort = reasoning_effort
        self._lock = threading.Lock()

    def complete(
        self, stage: str, system: str, user: str, model: str, json_mode: bool = False
    ) -> str:
        kw: dict[str, Any] = dict(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if json_mode:
            kw["text"] = {"format": {"type": "json_object"}}
        if model.startswith(("o1", "o3", "o4", "gpt-5")):
            kw["reasoning"] = {"effort": self.reasoning_effort}
        t0 = time.time()
        text = self._c.responses.create(**kw).output_text
        self._log(stage, model, system, user, text, time.time() - t0)
        return text

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        resp = self._c.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]

    def _log(self, stage, model, system, user, text, secs):
        if not self.log_path:
            return
        with self._lock, open(self.log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": utcnow(),
                        "stage": stage,
                        "model": model,
                        "input_hash": sha(system + "\n" + user),
                        "response": text,
                        "seconds": round(secs, 2),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
