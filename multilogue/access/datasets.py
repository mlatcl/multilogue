"""Named Access loaders — switch sources like ``pods.datasets.<name>()``.

Every public loader returns an Access bundle::

    {
      "units": list[Unit],
      "source": str,
      "citation": str,
      "license": str,
      "details": str,
      "path": str,
      "meta": dict,
    }
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from ..dummy import make_units
from ..protocols import Unit
from . import download as access_dl

Bundle = dict[str, Any]
Loader = Callable[..., Bundle]

_RESOURCES = access_dl.load_resources()


def list_sources() -> list[str]:
    """Registered source names (stable order from resources.json)."""
    return list(_RESOURCES.keys())


def get_resource(name: str) -> dict[str, Any]:
    if name not in _RESOURCES:
        known = ", ".join(list_sources())
        raise KeyError(f"Unknown source {name!r}. Known: {known}")
    return _RESOURCES[name]


def _bundle(
    source: str,
    units: list[Unit],
    *,
    path: Path | None = None,
    meta: dict[str, Any] | None = None,
) -> Bundle:
    r = get_resource(source)
    return {
        "units": units,
        "source": source,
        "citation": r.get("citation", ""),
        "license": r.get("license", ""),
        "details": r.get("details", ""),
        "path": str(path or access_dl.source_dir(source)),
        "meta": meta or {},
    }


def _unit(
    unit_id: str,
    doc_id: str,
    text: str,
    *,
    context: str = "",
    meta: dict[str, Any] | None = None,
) -> Unit:
    text = (text or "").strip()
    u: Unit = {
        "unit_id": str(unit_id),
        "doc_id": str(doc_id),
        "text": text,
        "extract_text": text,
        "context": context or "",
    }
    if meta:
        u["meta"] = meta
    return u


# ------------------------------------------------------------------ loaders


def synthetic(
    *,
    n_docs_per_group: int = 4,
    units_per_doc: int = 3,
    groups: tuple[str, ...] = ("group_a", "group_b"),
    **_: Any,
) -> Bundle:
    """In-memory synthetic units (no download)."""
    units = make_units(
        n_docs_per_group=n_docs_per_group,
        units_per_doc=units_per_doc,
        groups=groups,
    )
    return _bundle("synthetic", units, path=access_dl.source_dir("synthetic"), meta={"synthetic": True})


def polis(
    conversation: str | None = None,
    *,
    max_units: int | None = None,
    force: bool = False,
    **_: Any,
) -> Bundle:
    """Polis openData comments → units."""
    r = get_resource("polis")
    conv = conversation or r["default_conversation"]
    if conv not in r["conversations"]:
        # allow unknown folder names that exist upstream
        pass
    rel = f"{conv}/comments.csv"
    url = r["base_url"] + rel
    root = access_dl.ensure_files("polis", {rel: url}, force=force)
    path = root / rel
    units: list[Unit] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            body = (row.get("comment-body") or row.get("comment_body") or "").strip()
            if not body or row.get("moderated") in {"1", "true", "True"}:
                continue
            cid = row.get("comment-id") or row.get("comment_id") or str(len(units))
            units.append(
                _unit(
                    f"{conv}:{cid}",
                    conv,
                    body,
                    meta={
                        "author_id": row.get("author-id") or row.get("author_id"),
                        "agrees": row.get("agrees"),
                        "disagrees": row.get("disagrees"),
                        "source_file": str(path),
                    },
                )
            )
            if max_units is not None and len(units) >= max_units:
                break
    return _bundle("polis", units, path=path.parent, meta={"conversation": conv, "n_units": len(units)})


def gdn_cc(
    split: str | None = None,
    *,
    max_units: int | None = None,
    force: bool = False,
    text_field: str = "au_text",
    **_: Any,
) -> Bundle:
    """GDN-CC JSONL argumentative units → units."""
    r = get_resource("gdn_cc")
    split = split or r["default_split"]
    if split not in r["splits"]:
        raise ValueError(f"Unknown GDN-CC split {split!r}; use one of {list(r['splits'])}")
    fname = r["splits"][split]
    url = r["base_url"] + fname
    root = access_dl.ensure_files("gdn_cc", {fname: url}, force=force)
    path = root / fname
    units: list[Unit] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = (row.get(text_field) or row.get("opinion_text") or "").strip()
            if not text:
                continue
            uid = row.get("au_id") or f"{row.get('opinion_id')}-{len(units)}"
            doc = str(row.get("opinion_id") or "gdn")
            units.append(
                _unit(
                    str(uid),
                    doc,
                    text,
                    meta={"split": split, "opinion_id": row.get("opinion_id")},
                )
            )
            if max_units is not None and len(units) >= max_units:
                break
    return _bundle("gdn_cc", units, path=path, meta={"split": split, "n_units": len(units)})


def cdcp(
    *,
    subset: str = "train",
    max_units: int | None = None,
    force: bool = False,
    **_: Any,
) -> Bundle:
    """CDCP eRulemaking comments (``.txt``) → units."""
    r = get_resource("cdcp")
    zip_name = r["files"][0]
    url = r["urls"][0]
    root = access_dl.ensure_files("cdcp", {zip_name: url}, force=force)
    extract_dir = root / "extracted"
    marker = extract_dir / "cdcp"
    if force or not marker.is_dir():
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        access_dl.unzip(root / zip_name, extract_dir)
    # zip layout: cdcp/train|test/*.txt
    base = extract_dir / "cdcp" / subset
    if not base.is_dir():
        raise FileNotFoundError(f"CDCP subset not found: {base}")
    units: list[Unit] = []
    for txt in sorted(base.glob("*.txt")):
        text = txt.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        stem = txt.stem
        units.append(_unit(stem, f"cdcp/{subset}", text, meta={"path": str(txt)}))
        if max_units is not None and len(units) >= max_units:
            break
    return _bundle("cdcp", units, path=base, meta={"subset": subset, "n_units": len(units)})


def cimt(
    process: str | None = None,
    *,
    max_units: int | None = None,
    force: bool = False,
    **_: Any,
) -> Bundle:
    """CIMT German mobility participation TSV → units (one per sentence)."""
    r = get_resource("cimt")
    process = process or r["default_process"]
    processes: dict[str, str] = r["processes"]
    if process not in processes:
        raise ValueError(f"Unknown CIMT process {process!r}; use one of {list(processes)}")
    rel = processes[process]
    url = r["base_url"] + rel
    root = access_dl.ensure_files("cimt", {rel: url}, force=force)
    path = root / rel
    units: list[Unit] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            content = (row.get("content") or "").strip()
            if not content:
                continue
            doc = row.get("document_id") or process
            uid = row.get("id") or f"{doc}:{row.get('sentence_nr', len(units))}"
            units.append(
                _unit(
                    str(uid),
                    str(doc),
                    content,
                    meta={
                        "code": row.get("code"),
                        "process": process,
                        "url": row.get("url"),
                    },
                )
            )
            if max_units is not None and len(units) >= max_units:
                break
    return _bundle("cimt", units, path=path, meta={"process": process, "n_units": len(units)})


def decidim(
    resource: str | None = None,
    *,
    max_units: int | None = None,
    force: bool = False,
    **_: Any,
) -> Bundle:
    """Metadecidim open-data CSV → units."""
    r = get_resource("decidim")
    resource = resource or r["default_resource"]
    if resource not in r["resources"]:
        raise ValueError(f"Unknown Decidim resource {resource!r}; use one of {r['resources']}")
    fname = f"{resource}.csv"
    url = f"{r['base_url']}?export_format=CSV&resource={resource}"
    root = access_dl.ensure_files("decidim", {fname: url}, force=force)
    path = root / fname
    units: list[Unit] = []
    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            text = _decidim_text(row)
            if not text:
                continue
            uid = row.get("id") or str(len(units))
            doc = (
                row.get("participatory_space/id")
                or row.get("commentable_id")
                or row.get("component/id")
                or "decidim"
            )
            units.append(
                _unit(
                    str(uid),
                    str(doc),
                    text,
                    meta={"resource": resource, "url": row.get("url") or row.get("root_commentable_url")},
                )
            )
            if max_units is not None and len(units) >= max_units:
                break
    return _bundle("decidim", units, path=path, meta={"resource": resource, "n_units": len(units)})


def _decidim_text(row: dict[str, str]) -> str:
    for key in (
        "body",
        "body/en",
        "body/ca",
        "body/es",
        "title/en",
        "title/ca",
        "title/es",
        "title",
    ):
        val = (row.get(key) or "").strip()
        if val:
            return val
    # fall back: first non-empty body/* or title/*
    for k, v in row.items():
        if (k.startswith("body/") or k.startswith("title/")) and (v or "").strip():
            return v.strip()
    return ""


# ------------------------------------------------------------------ switch


_LOADERS: dict[str, Loader] = {
    "synthetic": synthetic,
    "polis": polis,
    "gdn_cc": gdn_cc,
    "cdcp": cdcp,
    "cimt": cimt,
    "decidim": decidim,
}


def load(source: str, **kwargs: Any) -> Bundle:
    """Load units from a named source (switchable Access entry point)."""
    if source not in _LOADERS:
        known = ", ".join(_LOADERS)
        raise KeyError(f"Unknown source {source!r}. Known: {known}")
    return _LOADERS[source](**kwargs)


def load_units(source: str, **kwargs: Any) -> list[Unit]:
    """Convenience: return only the unit list."""
    return load(source, **kwargs)["units"]
