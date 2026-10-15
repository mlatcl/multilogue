"""Synthetic units and a fake model for validation — no real dialogue data.

Generates in-memory units (and optional JSON under a caller-supplied directory).
Never ships participant transcripts. Safe for CI and local smoke runs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

# kind -> sentences; some concern lines carry "experience" markers for later consumers
BANK: dict[str, list[str]] = {
    "concern": [
        "I am worried the computer will make mistakes about benefits.",
        "I worry that my data could be sold to companies without consent.",
        "When I rang the council last year nobody could explain the decision.",
        "I fear older people will be left behind by online forms.",
        "My mum waited weeks because the system lost her housing form.",
        "I am worried about hackers getting into council records.",
    ],
    "benefit": [
        "It would help staff answer simple questions much faster.",
        "It could help spot potholes before they get dangerous.",
        "I think it would help match people to housing more fairly.",
        "It would help save money that could go back into services.",
    ],
    "condition": [
        "It must only be used if a human checks every decision.",
        "It must only be used if people are told when it is used.",
        "It must only be used if there is a clear way to complain.",
        "It must only be used if the data is stored securely.",
    ],
}

EXPERIENCE_MARKERS = ("When I rang", "My mum")
ALL = [(k, s) for k, ss in BANK.items() for s in ss]


def _sent(i: int, offset: int = 0) -> str:
    return ALL[(i + offset) % len(ALL)][1]


def make_units(
    *,
    n_docs_per_group: int = 4,
    units_per_doc: int = 3,
    groups: tuple[str, ...] = ("group_a", "group_b"),
) -> list[dict[str, Any]]:
    """Build synthetic units conforming to the multilogue Unit contract."""
    units: list[dict[str, Any]] = []
    n = 0
    for g in groups:
        for d in range(n_docs_per_group):
            doc_id = f"{g}/doc_{d:02d}"
            for u in range(units_per_doc):
                text = f"{_sent(n)} {_sent(n, 3)} That is my view on the topic."
                units.append(
                    {
                        "unit_id": f"u{n:04d}",
                        "doc_id": doc_id,
                        "text": text,
                        "extract_text": text,
                        "context": "",
                        "group": g,
                        "meta": {"synthetic": True},
                    }
                )
                n += 1
    return units


def write_units_json(units: list[dict[str, Any]], path: Path) -> Path:
    """Write units JSON for inspection. Caller must place this under a gitignored dir."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(units, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


class FakeClient:
    """Deterministic stand-in for completion/embedding. No network."""

    def __init__(self, fail_after: int | None = None, quota_error: bool = False):
        self.calls: list[str] = []
        self.fail_after = fail_after
        self.quota_error = quota_error

    def complete(self, stage, system, user, model, json_mode=False):
        self.calls.append(stage)
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError(
                "insufficient_quota" if self.quota_error else "temporary failure"
            )
        if stage.startswith(("ext_", "robust_")) or stage.rsplit("_", 1)[-1] in BANK:
            kind = stage.rsplit("_", 1)[-1]
            if kind not in BANK:
                kind = "concern"
            found = [s for s in BANK[kind] if s in user]
            if not found:
                return f"NO_{kind.upper()}"
            return "\n".join(f"- {' '.join(s.split()[:6])} || {s}" for s in found)
        if stage == "cluster_label":
            h = hashlib.md5(user.encode()).hexdigest()[:4]
            return json.dumps({"label": f"topic {h}", "description": "a synthetic topic"})
        if stage == "lens":
            ids = [int(m) for m in re.findall(r"^(\d+):", user, re.M)]
            return json.dumps(
                {
                    "lenses": [
                        {"name": "Lens A", "description": "even", "clusters": ids[::2]},
                        {"name": "Lens B", "description": "odd", "clusters": ids[1::2]},
                    ]
                }
            )
        raise AssertionError(f"unexpected stage {stage!r} for FakeClient")

    def embed(self, texts, model):
        out = []
        for t in texts:
            v = np.zeros(32, dtype=np.float64)
            for w in re.findall(r"[a-z]+", t.lower()):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 32] += 1
            out.append((v + 0.01).tolist())
        return out
