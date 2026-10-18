"""Embed phrases, soft MPPCA topics, blind labels, framing lenses.

CIP-0017: primary topic geometry is soft MPPCA (``multilogue.mppca``).
Hard MAP labels are a late harden view for LLM labelling / freeze tables.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
import yaml

from .mppca import (
    DEFAULT_TOPIC_SIGMA2,
    mppca_fit,
    responsibilities_to_labels,
)
from .text import get_list, parse_json, sha


class Embedder:
    """Embeddings cached on disk by phrase (lower-cased, stripped)."""

    def __init__(self, checkpoint_dir: Path, client, model: str):
        self.client = client
        self.model = model
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.vec_path = self.checkpoint_dir / f"embeddings_{model}.npy"
        self.idx_path = self.checkpoint_dir / f"embeddings_{model}_index.json"
        if self.vec_path.exists():
            self.vecs = np.load(self.vec_path)
        else:
            self.vecs = np.zeros((0, 0), np.float32)
        self.idx = json.loads(self.idx_path.read_text()) if self.idx_path.exists() else []
        self.pos = {h: i for i, h in enumerate(self.idx)}

    def __call__(self, texts: list[str]) -> np.ndarray:
        texts = [str(t) for t in texts]
        hashes = [sha(t.lower().strip()) for t in texts]
        if len(self.idx) != len(self.vecs):
            self.vecs, self.idx, self.pos = np.zeros((0, 0), np.float32), [], {}
        todo: dict[str, str] = {}
        for h, t in zip(hashes, texts):
            if h not in self.pos and h not in todo:
                todo[h] = t
        items = sorted(todo.items())
        for i in range(0, len(items), 256):
            batch = items[i : i + 256]
            vecs = np.array(
                self.client.embed([t for _, t in batch], self.model), dtype=np.float32
            )
            if len(vecs) != len(batch):
                raise RuntimeError(
                    f"The embedding service returned {len(vecs)} vectors for {len(batch)} phrases."
                )
            self.vecs = vecs if self.vecs.size == 0 else np.vstack([self.vecs, vecs])
            for h, _ in batch:
                self.pos[h] = len(self.idx)
                self.idx.append(h)
            np.save(self.vec_path, self.vecs)
            self.idx_path.write_text(json.dumps(self.idx))
        missing = [h for h in hashes if h not in self.pos]
        if missing:
            raise RuntimeError(
                f"{len(missing)} phrases still have no embedding (first: {missing[0][:12]})."
            )
        m = self.vecs[[self.pos[h] for h in hashes]]
        return m / np.linalg.norm(m, axis=1, keepdims=True)


def kmeans(X: np.ndarray, k: int, seed: int):
    """Deprecated hard k-means — prefer :func:`mppca_topics`.

    Kept for callers that explicitly want a hard baseline. New Address
    paths should use MPPCA (CIP-0017).
    """
    from sklearn.cluster import KMeans

    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(X)
    C = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
    return km.labels_, C


def mppca_topics(
    X: np.ndarray,
    k: int,
    seed: int,
    *,
    sigma2: float = DEFAULT_TOPIC_SIGMA2,
) -> dict[str, Any]:
    """Fit soft MPPCA topics; return responsibilities, means, and MAP labels."""
    fit = mppca_fit(X, k, sigma2=sigma2, seed=seed, n_init=10)
    R = np.asarray(fit["responsibilities"], dtype=float)
    means = np.asarray(fit["means"], dtype=float)
    labels = responsibilities_to_labels(R)
    return {
        "responsibilities": R,
        "means": means,
        "labels": labels,
        "sigma2": float(fit["sigma2"]),
        "pi": np.asarray(fit["pi"], dtype=float),
    }


def _member_mean_centroids(E: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    C = np.vstack(
        [
            E[labels == c].mean(0)
            if np.any(labels == c)
            else np.zeros(E.shape[1], dtype=float)
            for c in range(k)
        ]
    )
    norms = np.linalg.norm(C, axis=1, keepdims=True)
    return C / np.clip(norms, 1e-12, None)


def _load_soft_topic_checkpoint(
    phrases: pd.DataFrame,
    k: int,
    checkpoint_dir: Path,
    phrase_id_col: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Load soft MPPCA checkpoints if phrase ids and shapes match; else None."""
    R_path = checkpoint_dir / f"topic_responsibilities_k{k}.npy"
    means_path = checkpoint_dir / f"topic_means_k{k}.npy"
    ids_path = checkpoint_dir / f"topic_phrase_ids_k{k}.json"
    if not (R_path.exists() and means_path.exists() and ids_path.exists()):
        return None
    saved_ids = json.loads(ids_path.read_text(encoding="utf-8"))
    phrase_ids = phrases[phrase_id_col].tolist()
    R = np.load(R_path)
    means = np.load(means_path)
    if not (
        list(saved_ids) == phrase_ids
        and R.shape == (len(phrases), k)
        and means.shape[0] == k
    ):
        return None
    labels = responsibilities_to_labels(R)
    return labels, means, R


def frozen_or_new_assignments(
    phrases: pd.DataFrame,
    E: np.ndarray,
    k: int,
    seed: int,
    checkpoint_dir: Path,
    *,
    phrase_id_col: str = "phrase_id",
    replay: bool = False,
    freeze: bool = False,
    sigma2: float = DEFAULT_TOPIC_SIGMA2,
    return_soft: bool = False,
) -> tuple[np.ndarray, np.ndarray, bool] | tuple[np.ndarray, np.ndarray, bool, np.ndarray]:
    """Fit soft MPPCA topics (default) or explicitly reload a soft checkpoint.

    **Default (``freeze=False``):** always run ``mppca_fit`` and overwrite
    soft checkpoints. Hard ``cluster_assignments_k*.csv`` files are never
    used as topic geometry — that silent hard freeze is what kept formats
    on stale k-means after CIP-0017.

    **``freeze=True`` / ``replay=True``:** load soft
    ``topic_responsibilities_k{k}.npy`` + means when phrase ids match.
    ``replay=True`` raises if no soft checkpoint matches. Legacy hard-only
    CSVs are ignored.

    Returns
    -------
    labels, means, frozen
        MAP labels, L2-normalised component means μ, and whether this was
        an explicit freeze hit. If ``return_soft`` is True, also returns
        the responsibility matrix ``R``.
    """
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_dir / f"cluster_assignments_k{k}.csv"
    R_path = checkpoint_dir / f"topic_responsibilities_k{k}.npy"
    means_path = checkpoint_dir / f"topic_means_k{k}.npy"
    ids_path = checkpoint_dir / f"topic_phrase_ids_k{k}.json"
    phrase_ids = phrases[phrase_id_col].tolist()

    def _pack(labels, means, frozen, R):
        if return_soft:
            return labels, means, frozen, R
        return labels, means, frozen

    want_freeze = freeze or replay
    if want_freeze:
        loaded = _load_soft_topic_checkpoint(phrases, k, checkpoint_dir, phrase_id_col)
        if loaded is not None:
            labels, means, R = loaded
            return _pack(labels, means, True, R)
        if replay:
            raise RuntimeError(
                f"replay mode: no soft topic checkpoint matching these phrases "
                f"(expected {R_path.name}, {means_path.name}, {ids_path.name}). "
                f"Hard cluster_assignments CSVs are not used for topic geometry."
            )
        # freeze=True but nothing soft to load → fall through and fit

    fit = mppca_topics(E, k, seed, sigma2=sigma2)
    labels = fit["labels"]
    means = fit["means"]
    R = fit["responsibilities"]

    np.save(R_path, R)
    np.save(means_path, means)
    ids_path.write_text(json.dumps(phrase_ids), encoding="utf-8")
    pd.DataFrame({"phrase_id": phrases[phrase_id_col], "cluster": labels}).to_csv(
        path, index=False
    )
    ex_path = checkpoint_dir / f"cluster_examples_k{k}.json"
    if ex_path.exists():
        ex_path.unlink()
    return _pack(labels, means, False, R)


def example_phrases_for_clusters(
    phrases: pd.DataFrame,
    k: int,
    seed: int,
    *,
    phrase_col: str = "phrase",
    n_top: int = 12,
    n_sample: int = 6,
) -> list[dict[str, Any]]:
    """Build labelling units (examples + stable key) for each cluster."""
    cluster_units = []
    for c in range(k):
        sub = phrases[phrases.cluster == c].sort_values("centroid_sim", ascending=False)
        ex = sub[phrase_col].head(n_top).tolist()
        rest = sub[phrase_col].iloc[n_top:]
        if len(rest):
            ex += rest.sample(n=min(n_sample, len(rest)), random_state=seed).tolist()
        key = str(c) + "|" + sha("|".join(ex))[:10]
        cluster_units.append({"cluster": c, "examples": ex, "key": key})
    return cluster_units


def make_label_work(
    client,
    *,
    system: str,
    prompt_template: str,
    model: str,
    phrases_placeholder: str = "<<PHRASES>>",
) -> Callable[[dict], dict]:
    def work(cu: dict) -> dict:
        user = prompt_template.replace(
            phrases_placeholder, "\n".join(f"- {p}" for p in cu["examples"])
        )
        d = parse_json(
            client.complete("cluster_label", system, user, model=model, json_mode=True)
        )
        return {
            "label": str(d.get("label", f"cluster {cu['cluster']}"))[:80],
            "description": str(d.get("description", "")),
        }

    return work


def cluster_ids_from_lens_field(raw, k: int) -> list[int]:
    """Parse a lens ``clusters`` field into valid ids in ``0 .. k-1``.

    Models often return a bare count, a single int, or phrase-counts from the
    prompt instead of cluster ids — reject values outside the id range.
    """
    if raw is None or raw == "":
        return []
    if isinstance(raw, bool):
        return []
    if isinstance(raw, (int, float)):
        raw = [int(raw)]
    elif isinstance(raw, str):
        raw = re.findall(r"\d+", raw)
    elif not isinstance(raw, (list, tuple)):
        try:
            raw = list(raw)
        except TypeError:
            return []
    out: list[int] = []
    for c in raw:
        m = re.search(r"\d+", str(c))
        if not m:
            continue
        i = int(m.group())
        if 0 <= i < k:
            out.append(i)
    return out


def make_lens_work(
    client,
    *,
    system: str,
    prompt_template: str,
    cluster_description: str,
    model: str,
    k: int,
    clusters_placeholder: str = "<<CLUSTERS>>",
) -> Callable[[int], dict]:
    def work(run_number: int) -> dict:
        user = (
            prompt_template.replace(clusters_placeholder, cluster_description)
            + f"\n\nIMPORTANT: each lens \"clusters\" value must be a JSON array of "
            + f"integer ids in 0..{k - 1} — the number *before* the colon on each "
            + f"cluster line. Ignore n_phrases=… counts; never put those in "
            + f"\"clusters\". Every id must appear in exactly one lens.\n"
            + f"(run {run_number})"
        )
        d = parse_json(client.complete("lens", system, user, model=model, json_mode=True))
        mapping, descs = {}, {}
        for L in get_list(d, "lenses"):
            name = str(L.get("name", "")).strip() or "Unnamed"
            descs[name] = str(L.get("description", ""))
            for i in cluster_ids_from_lens_field(L.get("clusters"), k):
                mapping.setdefault(i, name)
        for c in range(k):
            mapping.setdefault(c, "Other")
        return {"mapping": {str(a): b for a, b in mapping.items()}, "descriptions": descs}

    return work


def resolve_lenses(
    k: int,
    lens_runs: dict,
    *,
    edited_mapping_path: str | Path | None = None,
) -> tuple[dict[int, str], bool]:
    """Lens of each cluster: researcher-edited YAML if provided, else lens run 1."""
    if edited_mapping_path:
        edited = yaml.safe_load(Path(edited_mapping_path).read_text(encoding="utf-8"))
        lens_of = {int(c): L for L, cs in edited.items() for c in cs}
        is_edited = True
    else:
        proposed = lens_runs.get("1", {"mapping": {str(c): "Other" for c in range(k)}})
        lens_of = {int(c): L for c, L in proposed["mapping"].items()}
        is_edited = False
    for c in range(k):
        lens_of.setdefault(c, "Other")
    return lens_of, is_edited


def lens_proposal_yaml(lens_runs: dict, names: dict[int, str]) -> str:
    by: dict[str, list[int]] = defaultdict(list)
    for c, L in lens_runs.get("1", {}).get("mapping", {}).items():
        by[L].append(int(c))
    lines = ["# Edit and point clustering.lens_mapping at this file."]
    for L, cs in sorted(by.items()):
        lines.append(
            f"{json.dumps(L)}: {sorted(cs)}   # "
            + "; ".join(names[c] for c in sorted(cs))[:150]
        )
    return "\n".join(lines) + "\n"
