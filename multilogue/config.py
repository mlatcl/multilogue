"""Settings and prompts loaders (YAML). Paths are consumer-owned; helpers stay generic."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


class Cfg(dict):
    """A dict whose keys can also be read as attributes (recursively)."""

    def __getattr__(self, name: str) -> Any:
        try:
            v = self[name]
        except KeyError as e:
            raise AttributeError(name) from e
        return Cfg(v) if isinstance(v, dict) and not isinstance(v, Cfg) else v

    __setattr__ = dict.__setitem__


def _merge(base: dict, extra: dict) -> dict:
    for k, v in (extra or {}).items():
        base[k] = (
            _merge(dict(base.get(k) or {}), v)
            if isinstance(v, dict) and isinstance(base.get(k), dict)
            else v
        )
    return base


def load_dotenv(path: str | Path | None = None, *, override: bool = False) -> Path | None:
    """Load KEY=VALUE pairs from a ``.env`` file into ``os.environ``."""
    candidates: list[Path] = []
    if path is not None:
        candidates.append(Path(path))
    else:
        if os.environ.get("MULTILOGUE_ROOT"):
            candidates.append(Path(os.environ["MULTILOGUE_ROOT"]) / ".env")
        candidates.append(Path.cwd() / ".env")
    seen: set[Path] = set()
    for raw in candidates:
        p = raw.resolve()
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            if s.startswith("export "):
                s = s[7:].strip()
            key, _, val = s.partition("=")
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if key and (override or key not in os.environ):
                os.environ[key] = val
        return p
    return None


def load_yaml(path: str | Path) -> Cfg:
    return Cfg(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})


def load_settings(
    path: str | Path,
    overrides: dict | None = None,
    local: str | Path | None = None,
) -> Cfg:
    """Load settings YAML, optionally merge a local overlay, then dotted ``overrides``."""
    cfg = load_yaml(path)
    if local is not None and Path(local).exists():
        _merge(cfg, yaml.safe_load(Path(local).read_text(encoding="utf-8")) or {})
    for k, v in (overrides or {}).items():
        cur = cfg
        parts = k.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return cfg


def load_prompts(path: str | Path) -> Cfg:
    return load_yaml(path)


def dump_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
