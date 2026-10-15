"""Optional litellm adapter. Install with ``pip install multilogue[litellm]``."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .llm import utcnow
from .text import sha


class LiteLLMClient:
    """Thin wrapper around litellm completion and embedding calls."""

    def __init__(self, log_path: Path | None = None):
        self._litellm = __import__("litellm")
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def complete(
        self, stage: str, system: str, user: str, model: str, json_mode: bool = False
    ) -> str:
        kw: dict[str, Any] = dict(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        t0 = time.time()
        resp = self._litellm.completion(**kw)
        text = resp.choices[0].message.content or ""
        self._log(stage, model, system, user, text, time.time() - t0)
        return text

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        resp = self._litellm.embedding(model=model, input=texts)
        data = resp.data if hasattr(resp, "data") else resp["data"]
        out = []
        for d in data:
            out.append(d["embedding"] if isinstance(d, dict) else d.embedding)
        return out

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
