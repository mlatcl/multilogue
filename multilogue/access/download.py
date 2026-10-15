"""Download and cache helpers (pods-style).

Cache root: ``MULTILOGUE_DATAPATH`` or ``~/.cache/multilogue``.
Set ``override_manual_authorize = True`` or ``MULTILOGUE_ACCESS_YES=1`` for CI.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

_PKG_DIR = Path(__file__).resolve().parent
_RESOURCES_PATH = _PKG_DIR / "resources.json"

override_manual_authorize = os.environ.get("MULTILOGUE_ACCESS_YES", "").lower() in {
    "1",
    "true",
    "yes",
    "y",
}


def default_datapath() -> Path:
    env = os.environ.get("MULTILOGUE_DATAPATH")
    if env:
        return Path(os.path.expanduser(os.path.expandvars(env))).resolve()
    return (Path.home() / ".cache" / "multilogue").resolve()


DATAPATH = default_datapath()


def set_datapath(path: str | Path) -> Path:
    """Override the cache root for the current process."""
    global DATAPATH
    DATAPATH = Path(os.path.expanduser(str(path))).resolve()
    DATAPATH.mkdir(parents=True, exist_ok=True)
    return DATAPATH


def load_resources() -> dict[str, Any]:
    with open(_RESOURCES_PATH, encoding="utf-8") as f:
        return json.load(f)


def source_dir(source: str, *parts: str) -> Path:
    p = DATAPATH / source
    for part in parts:
        p = p / part
    return p


def prompt_stdin(prompt: str) -> bool:
    yes, no = {"yes", "y"}, {"no", "n"}
    try:
        print(prompt)
        choice = input().strip().lower()
    except EOFError as e:
        raise RuntimeError(
            "No stdin for licence prompt. Set multilogue.access.download."
            "override_manual_authorize = True or MULTILOGUE_ACCESS_YES=1."
        ) from e
    if choice in yes:
        return True
    if choice in no:
        return False
    print(f"Please respond yes/y or no/n (got {choice!r}).")
    return prompt_stdin(prompt)


def authorize_download(
    source: str,
    resources: dict[str, Any] | None = None,
    *,
    prompt: Callable[[str], bool] | None = None,
) -> bool:
    if override_manual_authorize:
        return True
    resources = resources or load_resources()
    meta = resources[source]
    licence = meta.get("license") or "unspecified"
    details = meta.get("details") or source
    msg = (
        f"Download '{source}' into {DATAPATH / source}?\n"
        f"Licence: {licence}\n"
        f"{details}\n"
        "Type yes to continue: "
    )
    ask = prompt or prompt_stdin
    return ask(msg)


def download_url(url: str, dest: Path, *, messages: bool = True) -> Path:
    """Fetch ``url`` to ``dest`` (creates parents)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if messages:
        print(f"Downloading {url} -> {dest}")
    try:
        with urlopen(url) as resp:
            data = resp.read()
    except HTTPError as e:
        raise ValueError(f"HTTP {e.code} for {url}") from e
    except URLError as e:
        raise ValueError(f"Failed to fetch {url}: {e.reason}") from e
    dest.write_bytes(data)
    return dest


def unzip(archive: Path, dest_dir: Path) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest_dir)
    return dest_dir


def clear_cache(source: str | None = None) -> None:
    """Remove one source cache, or the entire datapath if ``source`` is None."""
    target = DATAPATH if source is None else DATAPATH / source
    if target.exists():
        shutil.rmtree(target)


def ensure_files(
    source: str,
    files: dict[str, str],
    *,
    resources: dict[str, Any] | None = None,
    force: bool = False,
) -> Path:
    """Ensure each logical name maps to a local file; download missing URLs.

    ``files`` maps relative cache path → absolute URL.
    """
    resources = resources or load_resources()
    root = source_dir(source)
    missing = {
        rel: url
        for rel, url in files.items()
        if force or not (root / rel).is_file()
    }
    if missing:
        if not authorize_download(source, resources):
            raise PermissionError(f"Download of {source!r} not authorised.")
        for rel, url in missing.items():
            download_url(url, root / rel)
    return root
